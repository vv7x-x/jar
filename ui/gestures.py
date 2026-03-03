class GestureControl:
    def __init__(self):
        pass

    def on_open_palm(self):
        return "expand"

    def on_closed_fist(self):
        return "shutdown"

    def on_swipe_right(self):
        return "confirm"

    def on_swipe_left(self):
        return "cancel"
