import logging
import os
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class Plugin():

    """

    Plugins are pluggable content which can be plugged
    into Caster.

    So far, only *Grammer* plugins exist.

    Plugins are active when the specified context is active.

    """

    def __init__(self, manager):

        self._id = self.__class__.__module__
        class_name = self.__class__.__name__
        self._name = f"{self._id}.{class_name}"

        self._manager = manager
        self._loaded = False

        self._grammars = []
        self._context = None

        self._state = None
        if self._manager and self._manager.state_directory:
            self._state = PluginState(os.path
                                      .join(self._manager.state_directory,
                                            f"{self._id}.state"))

        self._init_context()

    id = property(lambda self: self._id,
                  doc="Plugin id (`plugin_id`).")

    name = property(lambda self: self._name,
                    doc="Plugin name.")

    log = property(lambda self:
                   logging.getLogger(f"castervoice.Plugin({self._name})"),
                   doc="Get class logger.")

    def set_state(self, data):
        self._state.data = data

    state = property(lambda self: self._state.data if self._state else None,
                     set_state,
                     doc="Plugin state.")

    config = property(lambda self: self._manager.get_config(self._id),
                      doc="Plugin config.")

    grammars = property(lambda self: self._grammars,
                        doc="Plugin grammars.")

    def persist_state(self):
        self._state.persist()

    def _init_context(self):
        """Initialize Plugin to its default context.

        The plugin's default context can be overridden by user
        configuration.

        """
        try:
            self._context = self.get_context()
        except NotImplementedError:
            return

    def load(self):
        """Load plugin's grammars."""
        if not self._loaded:
            self.log.info("Loading ...")

            assert not self._grammars

            for grammar in self.get_grammars():
                self.log.info("Adding grammar: %s(%s)",
                              self._name, grammar.name)
                self._grammars.append(grammar)

            self.apply_context()

            for grammar in self._grammars:
                grammar.load()

            self._loaded = True

    def unload(self):
        """Unload plugin's grammars."""
        if self._loaded:
            self.log.info("Unloading ...")
            while len(self._grammars) > 0:
                _ = self._grammars.pop()
                del _

            self._grammars = []
            self._loaded = False

    def enable(self):
        """Enable plugin."""
        for grammar in self._grammars:
            self.log.info("Enabling grammar: %s(%s)",
                          self._name, grammar.name)
            grammar.enable()
            for rule in grammar.rules:
                rule.enable()

    def disable(self):
        """Disable plugin."""
        for grammar in self._grammars:
            self.log.info("Disabling grammar: %s(%s)",
                          self._name, grammar.name)
            for rule in grammar.rules:
                rule.disable()
            grammar.disable()

    def get_grammars(self):
        """Gather plugins' grammars.

        :returns: List of `Grammar`

        """
        return []

    def get_context(self, desired_state=None):
        """Get plugin context.

        The plugin's default context is returned when `desired_state`
        is `None`.
        `None` can be returned to indicate that no default context exists
        for this plugin.

        If `desired_state` is set returns a context object which matches
        the desired state. It is up to the plugin to document which
        context configurations are available.

        :param desired_state: Desired context state configuration
        :returns: Context

        """

        raise NotImplementedError(f"Plugin '{self._name}' does not provide any"
                                  " contexts")

    def apply_context(self, context=None):
        if context is not None:
            self._context = context

        if self._context is not None:
            self.log.info("Applying context '%s'", self._context)
            for grammar in self._grammars:
                grammar.set_context(self._context)

            self._apply_context(self._context)

    def _apply_context(self, context):
        """Child classes can override this method.

        Called after context is applied in `apply_context`.

        :param context: Context

        """


class PluginFile:

    def __init__(self, file_path):

        self._data = None
        self._type = self.__class__.__name__

        try:
            with open(file_path, "r", encoding="utf-8") as ymlfile:
                self._data = yaml.load(ymlfile, Loader=Loader)
        except yaml.YAMLError as error:
            print(f"Error in {self._type} file: {error}")
        except FileNotFoundError:
            pass

    def set_data(self, new_data):
        self._data = new_data

    def get_data(self):
        return self._data

    data = property(get_data, set_data)


class PluginState(PluginFile):

    def __init__(self, file_path):
        self._file_path = file_path
        super().__init__(file_path)

    def persist(self):
        with open(self._file_path, 'w', encoding="utf-8") as ymlfile:
            ymlfile.write(yaml.dump(self._data, Dumper=Dumper))
