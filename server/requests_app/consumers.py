import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        
        # Authenticated users only
        if not self.user or self.user.is_anonymous:
            await self.close(code=4003)  # Forbidden
            return
            
        self.group_name = 'dashboard_updates'
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Admin UI doesn't need to push data back to websocket,
        # but we can log or ignore any client messages
        pass

    async def send_dashboard_update(self, event):
        # Called when an event is sent to the group
        await self.send(text_data=json.dumps(event['data']))
