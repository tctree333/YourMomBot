import asyncio
from fastapi import APIRouter, Request, HTTPException
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from asyncio import Lock

from api import STAY_WARM_PERIOD
from api.schema import RequestBody
from api.model import YourMomModel
from api.logger import logger
from api.helper import repeat_every

lock = Lock()
router = APIRouter()
model = YourMomModel()


@router.on_event("startup")
@repeat_every(seconds=STAY_WARM_PERIOD)
def keep_warm():
    logger.info("keeping warm!")
    model.warm_up()


@router.get("/")
async def index():
    return {"msg": "Hello to the YourMom API!"}


@router.post("/yourmomify")
async def yourmomify(req: Request, body: RequestBody):
    if lock.locked():
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE, detail="Service busy"
        )
    async with lock:
        logger.info(f"msg: {body.msg}")
        outputs, scores = await model.async_yourmomify(body.msg)
        return {"input": body.msg, "response": outputs, "scores": scores}
