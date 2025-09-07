"""UPnP/DLNA client for discovering and accessing media servers like Fritz Box."""

import logging
import socket
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import requests
import time

logger = logging.getLogger(__name__)


@dataclass
class UPnPMediaFile:
    """Represents a media file discovered via UPnP/DLNA."""

    id: str
    title: str
    mime_type: str
    size: Optional[int] = None
    duration: Optional[str] = None
    url: str = ""
    path: str = ""


@dataclass
class UPnPMediaServer:
    """Represents a UPnP/DLNA media server."""

    name: str
    udn: str  # Unique Device Name
    base_url: str
    content_directory_url: str
    device: Any


class UPnPClient:
    """Client for discovering and browsing UPnP/DLNA media servers."""

    SUPPORTED_MIME_TYPES = {
        "video/mp4",
        "video/avi",
        "video/x-msvideo",
        "video/quicktime",
        "video/x-ms-wmv",
        "video/x-flv",
        "video/webm",
        "video/x-matroska",
        "audio/mpeg",
        "audio/mp3",
        "audio/flac",
        "audio/wav",
        "audio/aac",
        "audio/ogg",
        "audio/x-ms-wma",
        "audio/mp4",
    }

    SSDP_MULTICAST_IP = "239.255.255.250"
    SSDP_PORT = 1900

    def __init__(self):
        self.discovered_servers: List[UPnPMediaServer] = []
        self.connected_server: Optional[UPnPMediaServer] = None

    async def discover_media_servers(self, timeout: int = 10) -> List[UPnPMediaServer]:
        """Discover UPnP/DLNA media servers using SSDP."""
        logger.info("Discovering UPnP media servers via SSDP...")

        try:
            # Send SSDP M-SEARCH for MediaServer devices
            devices = await self._ssdp_discover(timeout)
            media_servers = []

            for device_info in devices:
                try:
                    server = await self._create_media_server_from_ssdp(device_info)
                    if server:
                        media_servers.append(server)
                        logger.info(f"Found media server: {server.name}")

                except Exception as e:
                    logger.warning(
                        f"Error processing device {device_info.get('location', 'unknown')}: {e}"
                    )
                    continue

            self.discovered_servers = media_servers
            logger.info(f"Discovered {len(media_servers)} media servers")
            return media_servers

        except Exception as e:
            logger.error(f"Error discovering UPnP devices: {e}")
            return []

    async def _ssdp_discover(self, timeout: int) -> List[Dict[str, str]]:
        """Perform SSDP discovery for MediaServer devices."""
        # SSDP M-SEARCH message for MediaServer devices
        ssdp_request = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {self.SSDP_MULTICAST_IP}:{self.SSDP_PORT}\r\n"
            'MAN: "ssdp:discover"\r\n'
            f"MX: {timeout}\r\n"
            "ST: urn:schemas-upnp-org:device:MediaServer:1\r\n"
            "\r\n"
        ).encode("utf-8")

        devices = []

        try:
            # Create UDP socket for SSDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(
                min(timeout, 5)
            )  # Cap individual socket timeout at 5 seconds

            # Send M-SEARCH request
            sock.sendto(ssdp_request, (self.SSDP_MULTICAST_IP, self.SSDP_PORT))

            # Collect responses
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode("utf-8", errors="ignore")

                    # Parse SSDP response
                    device_info = self._parse_ssdp_response(response)
                    if device_info and device_info not in devices:
                        devices.append(device_info)
                        logger.debug(
                            f"Found UPnP device at {device_info.get('location')}"
                        )

                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"Error receiving SSDP response: {e}")
                    continue

            sock.close()

        except Exception as e:
            logger.error(f"Error during SSDP discovery: {e}")

        return devices

    def _parse_ssdp_response(self, response: str) -> Optional[Dict[str, str]]:
        """Parse SSDP response headers."""
        try:
            lines = response.strip().split("\r\n")
            if not lines[0].startswith("HTTP/1.1 200 OK"):
                return None

            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().upper()] = value.strip()

            # We need at least the LOCATION header
            if "LOCATION" in headers:
                return {
                    "location": headers["LOCATION"],
                    "server": headers.get("SERVER", ""),
                    "st": headers.get("ST", ""),
                    "usn": headers.get("USN", ""),
                }

            return None

        except Exception as e:
            logger.debug(f"Error parsing SSDP response: {e}")
            return None

    async def _create_media_server_from_ssdp(
        self, device_info: Dict[str, str]
    ) -> Optional[UPnPMediaServer]:
        """Create a UPnPMediaServer from SSDP discovery info."""
        try:
            location = device_info.get("location")
            if not location:
                return None

            # Fetch device description
            response = requests.get(location, timeout=5)
            if response.status_code != 200:
                return None

            # Parse device XML
            root = ET.fromstring(response.content)

            # Define namespaces
            ns = {"upnp": "urn:schemas-upnp-org:device-1-0"}

            # Extract device info
            device_elem = root.find(".//upnp:device", ns)
            if device_elem is None:
                return None

            name = self._get_xml_text(
                device_elem, "upnp:friendlyName", ns, "Unknown Device"
            )
            udn = self._get_xml_text(device_elem, "upnp:UDN", ns, "")
            device_type = self._get_xml_text(device_elem, "upnp:deviceType", ns, "")

            # Check if it's a MediaServer
            if "MediaServer" not in device_type:
                return None

            # Find ContentDirectory service
            content_directory_url = None
            services = device_elem.find("upnp:serviceList", ns)
            if services is not None:
                for service in services.findall("upnp:service", ns):
                    service_type = self._get_xml_text(
                        service, "upnp:serviceType", ns, ""
                    )
                    if "ContentDirectory" in service_type:
                        control_url = self._get_xml_text(
                            service, "upnp:controlURL", ns, ""
                        )
                        if control_url:
                            # Make absolute URL
                            content_directory_url = urljoin(location, control_url)
                            break

            if not content_directory_url:
                logger.warning(f"No ContentDirectory service found for {name}")
                return None

            return UPnPMediaServer(
                name=name,
                udn=udn,
                base_url=location,
                content_directory_url=content_directory_url,
                device=device_info,
            )

        except Exception as e:
            logger.error(f"Error creating media server from SSDP: {e}")
            return None

    def _get_xml_text(
        self, element, tag: str, namespaces: Dict[str, str], default: str = ""
    ) -> str:
        """Get text content from XML element."""
        elem = element.find(tag, namespaces)
        return elem.text if elem is not None and elem.text else default

    def connect_to_server(self, server_name: Optional[str] = None) -> bool:
        """Connect to a specific media server or the first available one."""
        if not self.discovered_servers:
            logger.error("No media servers discovered")
            return False

        if server_name:
            # Find server by name
            for server in self.discovered_servers:
                if server_name.lower() in server.name.lower():
                    self.connected_server = server
                    logger.info(f"Connected to media server: {server.name}")
                    return True

            logger.error(f"Media server '{server_name}' not found")
            return False
        else:
            # Connect to first available server
            self.connected_server = self.discovered_servers[0]
            logger.info(f"Connected to media server: {self.connected_server.name}")
            return True

    async def browse_media_files(
        self, container_id: str = "0", max_depth: int = 2
    ) -> List[UPnPMediaFile]:
        """Browse media files from the connected server using ContentDirectory service."""
        if not self.connected_server:
            raise RuntimeError("Not connected to any media server")

        logger.info(
            f"Browsing media files from container '{container_id}' (max depth: {max_depth})"
        )

        try:
            media_files = []
            await self._browse_container_recursive(
                container_id, media_files, max_depth, 0
            )

            logger.info(f"Found {len(media_files)} media files")
            return media_files

        except Exception as e:
            logger.error(f"Error browsing media files: {e}")
            return []

    async def _browse_container_recursive(
        self,
        container_id: str,
        media_files: List[UPnPMediaFile],
        max_depth: int,
        current_depth: int,
    ):
        """Recursively browse containers to find media files."""
        if current_depth >= max_depth:
            return

        try:
            # Browse the current container
            items = await self._browse_container(container_id)

            for item in items:
                if item.get("upnp:class", "").startswith(
                    "object.item.audioItem"
                ) or item.get("upnp:class", "").startswith("object.item.videoItem"):
                    # This is a media file
                    media_file = self._create_media_file_from_item(item)
                    if media_file:
                        media_files.append(media_file)

                elif item.get("upnp:class", "").startswith("object.container"):
                    # This is a container, browse it recursively
                    child_id = item.get("id")
                    if child_id and current_depth + 1 < max_depth:
                        await self._browse_container_recursive(
                            child_id, media_files, max_depth, current_depth + 1
                        )

        except Exception as e:
            logger.warning(f"Error browsing container {container_id}: {e}")

    async def _browse_container(self, container_id: str) -> List[Dict[str, Any]]:
        """Browse a single container using SOAP ContentDirectory Browse action."""
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
            <ObjectID>{container_id}</ObjectID>
            <BrowseFlag>BrowseDirectChildren</BrowseFlag>
            <Filter>*</Filter>
            <StartingIndex>0</StartingIndex>
            <RequestedCount>1000</RequestedCount>
            <SortCriteria></SortCriteria>
        </u:Browse>
    </s:Body>
</s:Envelope>"""

        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": '"urn:schemas-upnp-org:service:ContentDirectory:1#Browse"',
            "Content-Length": str(len(soap_body)),
        }

        if not self.connected_server:
            raise RuntimeError("Not connected to any media server")

        try:
            response = requests.post(
                self.connected_server.content_directory_url,
                data=soap_body,
                headers=headers,
                timeout=10,
            )

            if response.status_code != 200:
                logger.warning(
                    f"SOAP request failed with status {response.status_code}"
                )
                return []

            # Parse the SOAP response
            return self._parse_browse_response(response.text)

        except Exception as e:
            logger.error(f"Error making SOAP request: {e}")
            return []

    def _parse_browse_response(self, soap_response: str) -> List[Dict[str, Any]]:
        """Parse SOAP Browse response and extract items."""
        try:
            root = ET.fromstring(soap_response)

            # Find the Result element in the SOAP response
            result_elem = None
            for elem in root.iter():
                if elem.tag.endswith("Result"):
                    result_elem = elem
                    break

            if result_elem is None or not result_elem.text:
                return []

            # Parse the DIDL-Lite XML inside the Result
            didl_xml = result_elem.text
            didl_root = ET.fromstring(didl_xml)

            items = []

            # Define namespaces for DIDL-Lite
            ns = {
                "didl": "urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/",
                "dc": "http://purl.org/dc/elements/1.1/",
                "upnp": "urn:schemas-upnp-org:metadata-1-0/upnp/",
            }

            # Extract containers and items
            for container in didl_root.findall(".//didl:container", ns):
                item_data = {
                    "id": container.get("id", ""),
                    "title": self._get_xml_text(container, "dc:title", ns),
                    "upnp:class": self._get_xml_text(container, "upnp:class", ns),
                    "type": "container",
                }
                items.append(item_data)

            for item in didl_root.findall(".//didl:item", ns):
                # Find the resource URL
                res_elem = item.find("didl:res", ns)
                resource_url = res_elem.text if res_elem is not None else ""

                item_data = {
                    "id": item.get("id", ""),
                    "title": self._get_xml_text(item, "dc:title", ns),
                    "upnp:class": self._get_xml_text(item, "upnp:class", ns),
                    "resource_url": resource_url,
                    "mime_type": (
                        res_elem.get("protocolInfo", "").split(":")[2]
                        if res_elem is not None
                        else ""
                    ),
                    "size": res_elem.get("size") if res_elem is not None else None,
                    "duration": (
                        res_elem.get("duration") if res_elem is not None else None
                    ),
                    "type": "item",
                }
                items.append(item_data)

            logger.debug(f"Parsed {len(items)} items from DIDL-Lite response")
            return items

        except Exception as e:
            logger.error(f"Error parsing SOAP response: {e}")
            return []

    def _create_media_file_from_item(
        self, item: Dict[str, Any]
    ) -> Optional[UPnPMediaFile]:
        """Create a UPnPMediaFile from a parsed DIDL-Lite item."""
        try:
            resource_url = item.get("resource_url", "")
            mime_type = item.get("mime_type", "")

            # Only process supported media types
            if not resource_url or mime_type not in self.SUPPORTED_MIME_TYPES:
                return None

            return UPnPMediaFile(
                id=item.get("id", ""),
                title=item.get("title", "Unknown"),
                mime_type=mime_type,
                size=int(item.get("size", 0)) if item.get("size") else None,
                duration=item.get("duration"),
                url=resource_url,
                path=resource_url,  # For UPnP, path and URL are the same
            )

        except Exception as e:
            logger.warning(f"Error creating media file from item: {e}")
            return None

    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the connected server."""
        if not self.connected_server:
            return None

        return {
            "name": self.connected_server.name,
            "udn": self.connected_server.udn,
            "base_url": self.connected_server.base_url,
            "content_directory_url": self.connected_server.content_directory_url,
            "type": "UPnP/DLNA Media Server",
        }


async def discover_fritz_box_media_server() -> Optional[UPnPMediaServer]:
    """Discover Fritz Box media server specifically."""
    client = UPnPClient()
    servers = await client.discover_media_servers()

    # Look for Fritz Box specifically
    for server in servers:
        if "fritz" in server.name.lower() or "avm" in server.name.lower():
            logger.info(f"Found Fritz Box media server: {server.name}")
            return server

    # Return first available server if no Fritz Box found
    if servers:
        logger.info(
            f"No Fritz Box found, using first available server: {servers[0].name}"
        )
        return servers[0]

    return None
