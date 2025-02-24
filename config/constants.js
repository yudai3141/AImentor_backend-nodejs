require('dotenv').config();

module.exports = {
  API_ENDPOINTS: {
    FASTAPI: process.env.FASTAPI_BASE_URL || 'http://localhost:8000',
    SELF: process.env.NODEJS_BASE_URL || 'http://localhost:5002',
    FRONTEND: process.env.FRONTEND_BASE_URL || 'http://localhost:3000'
  }
}; 