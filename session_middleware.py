from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
import motor.motor_asyncio
import uuid

class MongoDBSessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key: str, mongo_url: str, max_age: int = 3600):
        super().__init__(app)
        self.signer = TimestampSigner(secret_key)
        self.max_age = max_age
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
        self.db = self.client['session_db']
        self.collection = self.db['sessions']

async def dispatch(self, request: StarletteRequest, call_next):
    session_id = request.cookies.get('fastapi_session_id')
    request.state.session = {}

    new_session = False

    if session_id:
        try:
            session_id = self.signer.unsign(session_id, max_age=self.max_age).decode()
            session_data = await self.collection.find_one({'_id': session_id})
            if session_data:
                request.state.session = session_data['data']
            else:
                new_session = True
        except (BadSignature, SignatureExpired):
            session_id = None
            new_session = True
    else:
        new_session = True

    if new_session:
        session_id = str(uuid.uuid4())

    response = await call_next(request)

    # セッションデータを保存
    signed_session_id = self.signer.sign(session_id).decode()
    await self.collection.update_one({'_id': session_id}, {'$set': {'data': request.state.session}}, upsert=True)
    response.set_cookie('fastapi_session_id', signed_session_id, max_age=self.max_age, httponly=True)

    return response