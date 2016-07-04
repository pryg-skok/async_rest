#!/usr/bin/env python3

from aiohttp import web
import motor.motor_asyncio
from bson import json_util, ObjectId


async def substract(request):
    """ return tree substract where root is element id """
    db = request.app["db"]
    elid = request.match_info.get("id")
    if ObjectId.is_valid(elid):
        els = []
        async for el in db.tree.find(
            {"$or": [{"ancestors": ObjectId(elid)}, {"_id": ObjectId(elid)}]}):
            els.append(el)
        return web.json_response(els, dumps=json_util.dumps)
    return web.json_response(status=404)


async def insert(request):
    """ return tree substract where root is element id """
    db = request.app["db"]
    parent_id = request.GET.get("parent_id")
    text = request.GET.get("text", "")
    ancestors = []
    if ObjectId.is_valid(parent_id):
        parent = await db.tree.find_one({"_id": ObjectId(parent_id)})
        if parent:
            parent_id = parent["_id"]
            ancestors = parent["ancestors"]
            ancestors.append(parent_id)
        else:
            parent_id = None
    else:
        parent_id = None
    el = await db.tree.insert({
        "text": text,
        "parent": parent_id,
        "ancestors": ancestors
    })
    return web.json_response(el, dumps=json_util.dumps)


async def search(request):
    """ perform full text search """
    search_query = request.match_info.get("text")
    db = request.app["db"]
    els = []
    async for el in db.tree.find({"$text": {"$search": search_query}}):
        el["abspath"] = "/" + "/".join([str(e) for e in el["ancestors"]] + [str(el["_id"])])
        els.append(el)
    return web.json_response(els, dumps=json_util.dumps)


def init_app():
    app = web.Application()
    db = motor.motor_asyncio.AsyncIOMotorClient()
    db.test.tree.create_index([("text", "text")])
    app["db"] = db.test
    app.router.add_route("GET", "/sub/{id}", substract)
    app.router.add_route("GET", "/search/{text}", search)
    app.router.add_route("POST", "/new", insert)
    return app


if __name__ == "__main__":
    web.run_app(init_app())
