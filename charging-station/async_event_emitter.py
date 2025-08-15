class AsyncEventEmitter:
    def __init__(self):
        self._listeners = {}

    def on(self, event_name, callback):
        self._listeners.setdefault(event_name, []).append(callback)

    async def emit(self, event_name, *args, **kwargs):
        for callback in self._listeners.get(event_name, []):
            await callback(event_name, *args, **kwargs)