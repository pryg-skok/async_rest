#!/usr/bin/env python3

from urllib.parse import parse_qs
from os.path import join as pjoin
from aiohttp import web
import motor.motor_asyncio
from bson import json_util, ObjectId


async def substract(request):
    """ return tree substract where root is element id """
    db = request.app["db"]
    elid = request.match_info.get("id")
    if ObjectId.is_valid(elid):
        el = await db.tree.find_one({"_id": ObjectId(elid)})
        if not el:
            return web.json_response(status=404)
        else:
            el["parent"] = None
            return web.json_response(el, dumps=json_util.dumps)
    return web.json_response(status=404)


async def insert(request):
    """ return tree substract where root is element id """
    db = request.app["db"]
    query = parse_qs(request.query_string, keep_blank_values=True)
    parent_id = query.get("parent_id", [""])[0]
    text = query.get("text", [])
    abspath = "/"
    if ObjectId.is_valid(parent_id):
        parent = await db.tree.find_one({"_id": ObjectId(parent_id)})
        if parent:
            parent_id = parent["_id"]
            abspath = pjoin("/", str(parent["abspath"]), str(parent_id))
        else:
            parent_id = None
    else:
        parent_id = None
    el = await db.tree.insert({
        "text": " ".join(text),
        "parent": parent_id,
        "abspath": abspath,
        "ancestors": []
    })
    if parent_id:
        await db.tree.update({"_id": parent_id}, {"$push": {"ancestors": el}})
    return web.json_response(el, dumps=json_util.dumps)


async def search(request):
    """ perform full text search """
    search_query = request.match_info.get("text")
    db = request.app["db"]
    els = []
    async for el in db.tree.find({"$text": {"$search": search_query}}):
        els.append(el)
    return web.json_response(els, dumps=json_util.dumps)


def init_app():
    app = web.Application()
    db = motor.motor_asyncio.AsyncIOMotorClient()
    db.test.tree.create_index([("text", "text")])
    app["db"] = db.test
    app.router.add_route("GET", "/sub/{id}", substract)
    app.router.add_route("GET", "/search/{text}", search)
    app.router.add_route("POST", "/new/", insert)
    return app


if __name__ == "__main__":
    web.run_app(init_app())
