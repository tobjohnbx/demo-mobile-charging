import asyncio

async def inform_partner(event_name, *args,**kwargs):
    await asyncio.sleep(2)
    print("Informed partner")
    print(event_name)
    print(args)
    print(kwargs)