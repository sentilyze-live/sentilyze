"""
Sentilyze Agent Gateway
FastAPI-based API Gateway for AI Agent interactions
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import httpx
from datetime import datetime
import jwt
from passlib.context import CryptContext

# Initialize FastAPI app
app = FastAPI(
    title="Sentilyze AI Agent Gateway",
    description="API Gateway for AI Agent Squad - Yatırım tavsiyesi vermez",
    version="1.0.0"
)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration
AGENT_ORCHESTRATOR_URL = os.getenv('AGENT_ORCHESTRATOR_URL', 'https://agent-orchestrator-hash.a.run.app')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatRequest(BaseModel):
    user_id: str
    message: str
    agent_type: str = Field(default='insight', pattern='^(insight|risk|interpreter|watchlist|concierge)$')
    session_id: Optional[str] = None
    asset: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    agent_type: str
    session_id: str
    compliance: str
    response_time_ms: int
    sentiment_data: Optional[List[Dict]] = None
    disclaimer: str = "Yatırım tavsiyesi değildir. Kripto varlıklar yüksek risk içerir."

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    agents: List[str]
    version: str

class AgentInfo(BaseModel):
    agent_type: str
    name: str
    name_tr: Optional[str] = None
    description: str
    description_tr: Optional[str] = None
    capabilities: List[str]
    disclaimer: str
    disclaimer_tr: Optional[str] = None

# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Rate limiting (simple implementation)
request_counts: Dict[str, List[datetime]] = {}

async def rate_limit_check(user_id: str):
    """Check rate limit (10 requests per minute)"""
    now = datetime.now()
    if user_id not in request_counts:
        request_counts[user_id] = []
    
    # Remove old requests
    request_counts[user_id] = [
        req_time for req_time in request_counts[user_id]
        if (now - req_time).seconds < 60
    ]
    
    if len(request_counts[user_id]) >= 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (10 req/min)")
    
    request_counts[user_id].append(now)

# Middleware for logging and headers
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and add compliance headers"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    # Add compliance headers
    response.headers["X-Disclaimer"] = "Yatırım tavsiyesi değildir"
    response.headers["X-Compliance"] = "SPK-Mevzuat-Uyumlu"
    
    return response

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="agent-gateway",
        timestamp=datetime.now().isoformat(),
        agents=["insight", "risk", "interpreter", "watchlist", "concierge"],
        version="1.0.0"
    )

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(verify_token)
):
    """
    Send a message to an AI agent
    
    - **user_id**: Unique user identifier
    - **message**: User's message
    - **agent_type**: Type of agent (insight, risk, interpreter, watchlist, concierge)
    - **session_id**: Optional session ID for conversation continuity
    - **asset**: Optional asset symbol (BTC, ETH, XAU, etc.)
    """
    
    # Rate limiting
    await rate_limit_check(request.user_id)
    
    try:
        # Call agent orchestrator
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AGENT_ORCHESTRATOR_URL}/chat",
                json={
                    "user_id": request.user_id,
                    "message": request.message,
                    "agent_type": request.agent_type,
                    "session_id": request.session_id,
                    "asset": request.asset
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Agent service error"
                )
            
            data = response.json()
            
            return ChatResponse(
                response=data.get('response', ''),
                agent_type=data.get('agent_type', request.agent_type),
                session_id=data.get('session_id', ''),
                compliance=data.get('compliance', 'UNKNOWN'),
                response_time_ms=data.get('response_time_ms', 0),
                sentiment_data=data.get('sentiment_data'),
                disclaimer="Yatırım tavsiyesi değildir. Kripto varlıklar yüksek risk içerir."
            )
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Agent service unavailable: {str(e)}"
        )

# Agent info endpoint
@app.get("/agents/{agent_type}", response_model=AgentInfo)
async def get_agent_info(agent_type: str):
    """Get information about a specific agent"""
    
    agents_info = {
        'insight': AgentInfo(
            agent_type='insight',
            name='Insight Navigator',
            description='Piyasa sentimenti ve trend analizi sunar',
            capabilities=[
                'Sosyal medya sentiment analizi',
                'Trend takibi',
                'Teknik gösterge açıklamaları',
                'Hacim analizi',
                'Korelasyon analizi'
            ],
            disclaimer='Yatırım tavsiyesi değildir. Sadece eğitim ve bilgilendirme amaçlıdır.'
        ),
        'risk': AgentInfo(
            agent_type='risk',
            name='Risk Guardian',
            description='Risk eğitimi ve piyasa uyarıları',
            capabilities=[
                'Risk eğitimi',
                'Volatilite monitoring',
                'Risk toleransı değerlendirmesi',
                'Finansal okuryazarlık',
                'Portföy çeşitlendirme eğitimi'
            ],
            disclaimer='Yatırım tavsiyesi değildir. Eğitim amaçlıdır.'
        ),
        'interpreter': AgentInfo(
            agent_type='interpreter',
            name='Data Interpreter',
            description='Teknik göstergeler ve veri açıklamaları',
            capabilities=[
                'Teknik gösterge açıklamaları',
                'Grafik okuma eğitimi',
                'Model confidence açıklaması',
                'Korelasyon analizi eğitimi',
                'Veri kaynağı açıklamaları'
            ],
            disclaimer='Yatırım tavsiyesi değildir. Eğitim amaçlıdır.'
        ),
        'watchlist': AgentInfo(
            agent_type='watchlist',
            name='Watchlist Manager',
            name_tr='Watchlist Manager',
            description='Watchlist and price alert tracking (user-selected assets only)',
            description_tr='İzleme listesi ve fiyat alarm takibi (kullanıcının kendi seçtiği varlıklar)',
            capabilities=[
                'Watchlist management / İzleme listesi yönetimi',
                'Price alert setup / Fiyat alarmı kurma',
                'Alert list viewing / Alarm listesi görüntüleme',
                'Personal tracking (your data only) / Kişisel takip (sadece kendi veriniz)'
            ],
            disclaimer='Not investment advice. For informational purposes only.',
            disclaimer_tr='Yatırım tavsiyesi değildir. Sadece bilgilendirme amaçlıdır.'
        ),
        'concierge': AgentInfo(
            agent_type='concierge',
            name='Platform Guide',
            description='Platform rehberi ve kullanım yardımı',
            capabilities=[
                'Platform tanıtımı',
                'Dashboard kullanım rehberi',
                'Özellik açıklamaları',
                'SSS',
                'KVKK ve gizlilik bilgileri'
            ],
            disclaimer='Yatırım tavsiyesi değildir.'
        )
    }
    
    if agent_type not in agents_info:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agents_info[agent_type]

# List all agents
@app.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """List all available agents"""
    agents = []
    for agent_type in ['insight', 'risk', 'interpreter', 'watchlist', 'concierge']:
        agent_info = await get_agent_info(agent_type)
        agents.append(agent_info)
    return agents

# Alert webhooks (for Pub/Sub push subscriptions)
@app.post("/alerts/risk")
async def risk_alert_webhook(request: Request):
    """Receive risk alerts from Pub/Sub"""
    try:
        body = await request.body()
        # Process risk alert
        # Could send push notification, email, etc.
        return {"status": "received"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/alerts/price")
async def price_alert_webhook(request: Request):
    """Receive price alerts from Pub/Sub"""
    try:
        body = await request.body()
        # Process price alert
        return {"status": "received"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with compliance headers"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "disclaimer": "Yatırım tavsiyesi değildir. Kripto varlıklar yüksek risk içerir."
        },
        headers={
            "X-Disclaimer": "Yatırım tavsiyesi değildir",
            "X-Compliance": "SPK-Mevzuat-Uyumlu"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on startup"""
    print("Agent Gateway started")
    print(f"Agent Orchestrator URL: {AGENT_ORCHESTRATOR_URL}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown"""
    print("Agent Gateway shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
