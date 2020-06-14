import sys

from xbmcgui import WindowXMLDialog, ACTION_PARENT_DIR, ACTION_NAV_BACK, ACTION_PREVIOUS_MENU, ListItem

from lib.api.flix.kodi import ADDON_PATH


def dialog_select(title):
    return DialogSelect("plugin.video.flix-dialog-select-large.xml", ADDON_PATH, "Default", title=title)


# noinspection PyUnresolvedReferences
class DialogSelect(WindowXMLDialog):
    _close_button_id = 32500
    _title_label_id = 32501
    _panel_id = 32503
    _index_property = "_index"

    def __init__(self, *args, **kwargs):
        super(DialogSelect, self).__init__(*args, **kwargs)
        self._title = kwargs.get("title", "")
        self._selected = -1
        self._items = []

    def set_title(self, title):
        self._title = title

    def add_item(self, label="", label2="", icon=""):
        item = ListItem(label, label2)
        if icon:
            item.setArt({"icon": icon})
        self.addItem(item)

    def addItem(self, item, position=sys.maxsize):
        self._items.insert(position, item)

    def addItems(self, items):
        self._items.extend(items)

    def onInit(self):
        self.getControl(self._title_label_id).setLabel(self._title)
        panel = self.getControl(self._panel_id)
        for index, item in enumerate(self._items):
            item.setProperty(self._index_property, str(index))
            panel.addItem(item)

    def onClick(self, control_id):
        if control_id == self._close_button_id:
            # Close Button
            self.close()
        elif control_id == self._panel_id:
            # Panel
            self._selected = int(self.getControl(self._panel_id).getSelectedItem().getProperty(self._index_property))
            self.close()

    def onAction(self, action):
        if action.getId() in (ACTION_PARENT_DIR, ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self.close()

    @property
    def selected(self):
        return self._selected
