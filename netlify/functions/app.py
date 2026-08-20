from mangum import Mangum
from app import app  # Imports top-level FastAPI app instance

handler = Mangum(app, lifespan="off")
