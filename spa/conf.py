import importlib
import os

import global_settings

ENVIRONMENT_VARIABLE = "SPA_CONFIG"


class Settings(object):

    SETTINGS_MODULE = None
    configured = False

    def __getattr__(self, attr):
        if not self.configured:
            self._setup(attr)
        return self.__dict__[attr]

    def _setup(self, attr=None, settings_module=None):
        """
        Load the settings file pointed to by the environment variable.
        """
        settings_module = os.environ.get(ENVIRONMENT_VARIABLE, settings_module)
        if not settings_module:
            desc = ("setting %s" % attr) if attr else "settings"
            raise RuntimeError(
                "Requested %s, but settings are not configured. "
                "You must either define the environment variable %s "
                "or call settings.configure() before accessing settings."
                % (desc, ENVIRONMENT_VARIABLE))

        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting.isupper():
                setattr(self, setting, getattr(global_settings, setting))

        # store the settings module in case someone later cares
        self.SETTINGS_MODULE = settings_module

        self._process(importlib.import_module(self.SETTINGS_MODULE))

    def _process(self, mod):
        for setting in dir(mod):
            if setting.isupper():
                setting_value = getattr(mod, setting)
                setattr(self, setting, setting_value)

        self.configured = True

        # tuple_settings = (
        #     "ALLOWED_INCLUDE_ROOTS",
        #     "INSTALLED_APPS",
        #     "TEMPLATE_DIRS",
        #     "LOCALE_PATHS",
        # )
        # self._explicit_settings = set()
        # for setting in dir(mod):
        #     if setting.isupper():
        #         setting_value = getattr(mod, setting)
        #
        #         if (setting in tuple_settings and
        #                 isinstance(setting_value, six.string_types)):
        #             raise ImproperlyConfigured("The %s setting must be a tuple. "
        #                     "Please fix your settings." % setting)
        #         setattr(self, setting, setting_value)
        #         self._explicit_settings.add(setting)
        #
        # if not self.SECRET_KEY:
        #     raise ImproperlyConfigured("The SECRET_KEY setting must not be empty.")

        # if ('django.contrib.auth.middleware.AuthenticationMiddleware' in self.MIDDLEWARE_CLASSES and
        #         'django.contrib.auth.middleware.SessionAuthenticationMiddleware' not in self.MIDDLEWARE_CLASSES):
        #     warnings.warn(
        #         "Session verification will become mandatory in Django 1.10. "
        #         "Please add 'django.contrib.auth.middleware.SessionAuthenticationMiddleware' "
        #         "to your MIDDLEWARE_CLASSES setting when you are ready to opt-in after "
        #         "reading the upgrade considerations in the 1.8 release notes.",
        #         RemovedInDjango110Warning
        #     )

    def configure(self, default_settings=global_settings, **options):
        """
        Called to manually configure the settings. The 'default_settings'
        parameter sets where to retrieve any unspecified values from (its
        argument must support attribute access (__getattr__)).
        """
        if self.configured:
            raise RuntimeError('Settings already configured.')
        self._process(default_settings)
        for name, value in options.items():
            setattr(self, name, value)


settings = Settings()
