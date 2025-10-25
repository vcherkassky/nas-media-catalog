const express = require('express');
const axios = require('axios');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// API proxy routes to avoid CORS issues
app.get('/api/*', async (req, res) => {
  try {
    const apiPath = req.path.replace('/api', '');
    const queryString = req.url.split('?')[1] || '';
    const fullUrl = `${API_BASE_URL}${apiPath}${queryString ? '?' + queryString : ''}`;
    
    console.log(`Proxying GET request to: ${fullUrl}`);
    
    // Special handling for download endpoints
    if (apiPath.includes('/download')) {
      const response = await axios.get(fullUrl, { responseType: 'stream' });
      
      // Forward headers from the API response
      if (response.headers['content-type']) {
        res.set('Content-Type', response.headers['content-type']);
      }
      if (response.headers['content-disposition']) {
        res.set('Content-Disposition', response.headers['content-disposition']);
      }
      
      // Pipe the response directly without JSON serialization
      response.data.pipe(res);
    } else {
      // Regular JSON responses
      const response = await axios.get(fullUrl);
      res.json(response.data);
    }
  } catch (error) {
    console.error('API proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.message,
      details: error.response?.data || 'Unknown error'
    });
  }
});

app.post('/api/*', async (req, res) => {
  try {
    const apiPath = req.path.replace('/api', '');
    const fullUrl = `${API_BASE_URL}${apiPath}`;
    
    console.log(`Proxying POST request to: ${fullUrl}`);
    const response = await axios.post(fullUrl, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('API proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.message,
      details: error.response?.data || 'Unknown error'
    });
  }
});

app.delete('/api/*', async (req, res) => {
  try {
    const apiPath = req.path.replace('/api', '');
    const fullUrl = `${API_BASE_URL}${apiPath}`;
    
    console.log(`Proxying DELETE request to: ${fullUrl}`);
    const response = await axios.delete(fullUrl);
    res.json(response.data);
  } catch (error) {
    console.error('API proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.message,
      details: error.response?.data || 'Unknown error'
    });
  }
});

// Serve the main HTML file
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`NAS Media Catalog UI running on http://localhost:${PORT}`);
  console.log(`Proxying API requests to: ${API_BASE_URL}`);
});
