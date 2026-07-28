from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .registry import GROUP, registry


class DevicesConsumer(AsyncJsonWebsocketConsumer):
    """Pushes full device snapshots to the dashboard."""

    async def connect(self):
        await self.channel_layer.group_add(GROUP, self.channel_name)
        await self.accept()
        await self.send_json(registry.snapshot())

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GROUP, self.channel_name)

    async def devices_update(self, event):
        await self.send_json(event["payload"])
