# Apache Local Community Taipei AI Agent

一個基於RAG（檢索增強生成）技術的AI助手，專門為Apache Local Community Taipei社群設計，能夠回答關於社群成員、專案和活動的問題。

## Features

- **AI Assistant "小饅頭"**: Friendly AI agent for Apache Local Community Taipei
- **RAG Technology**: Intelligent Q&A based on Slack and GitHub data
- **Semantic Search**: Precise matching using Gemini embedding models
- **Natural Conversation**: Supports Traditional Chinese with concise and friendly responses

## Technical Architecture

- **Backend**: Python + FastAPI + PostgreSQL + FAISS
- **Frontend**: React + TypeScript + Tailwind CSS
- **AI Models**: Grok-4 (OpenRouter) + Gemini Embeddings
- **Data Sources**: Slack API + GitHub API
- **Deployment**: Docker Compose + Nginx

## Quick Start

### 1. Clone the Project

```bash
git clone https://github.com/rich7420/community-ai-agent.git
cd community-ai-agent
```

### 2. Environment Setup

Copy the environment variables template:

```bash
cp env.example .env
```

Edit the `.env` file with your API keys:

```bash
# Slack Configuration
SLACK_APP_ID=your-slack-app-id
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_VERIFICATION_TOKEN=your-slack-verification-token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# GitHub Configuration
GITHUB_TOKEN=ghp_your-github-token

# Grok via OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key

# Google AI API (for Gemini embeddings)
GOOGLE_API_KEY=your-google-api-key

# Database Configuration
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://postgres:your-secure-password@postgres:5432/community_ai

# MinIO Configuration
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key

# Redis Configuration
REDIS_PASSWORD=your-redis-password
```

### 3. Start Services

```bash
docker compose up -d
```

The system will automatically:
- Start all services (PostgreSQL, Redis, MinIO, API, Frontend)
- Wait for dependency services health checks to pass
- Automatically initialize data collection (Slack and GitHub data)
- Generate embeddings and build FAISS index
- Start API services

### 4. Access the Application

- **Frontend Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Key Setup

### Slack API
1. Visit [Slack API](https://api.slack.com/apps)
2. Create a new app
3. Get Bot Token and App Token
4. Set up OAuth redirect URLs

### GitHub API
1. Visit [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a new Personal Access Token
3. Select `repo` and `read:org` permissions

### OpenRouter API
1. Visit [OpenRouter](https://openrouter.ai/)
2. Register an account
3. Get API Key

### Google AI API
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API Key

## Project Structure

```
community-ai-agent/
├── src/                    # Backend source code
│   ├── ai/                 # AI-related modules
│   ├── api/                # API endpoints
│   ├── collectors/         # Data collectors
│   ├── storage/            # Data storage
│   └── ...
├── frontend-react/         # Frontend source code
│   ├── src/               # React components
│   ├── public/            # Static assets
│   └── ...
├── docker-compose.yml     # Docker orchestration
├── env.example           # Environment variables template
└── README.md            # Project documentation
```

## Development Guide

### Local Development

```bash
# Backend development
cd src
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Frontend development
cd frontend-react
npm install
npm run dev
```

### Testing

```bash
# Run tests
python -m pytest tests/

# Test API connections
python tests/test_api_connections.py
```

## Deployment

### Local Development Deployment

```bash
# Using startup script (recommended)
./start.sh

# Or using universal deployment script
./deploy.sh dev
```

### Debian Deployment

```bash
# Local Debian (Docker installed)
./deploy-debian.sh --local

# GCP Debian (full setup)
./deploy-debian.sh --gcp

# Or using universal deployment script
./deploy.sh debian
```

### Production Deployment

1. Set up production environment variables
2. Configure SSL certificates
3. Set up domain and DNS
4. Run deployment script

```bash
./deploy.sh
```

### Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
- **MinIO Console**: http://localhost:9001

## Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or suggestions, please:

1. Check the [documentation](docs/)
2. Open an [Issue](https://github.com/rich7420/community-ai-agent/issues)
3. Contact the maintainers

## Acknowledgments

- Apache Local Community Taipei community
- All contributors and test users
- Open source community support

---

**Note**: Please ensure not to commit `.env` files containing real API keys to version control systems.