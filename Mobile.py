from typing import Dict, Optional, Tuple
import time, os, configparser, re
from lxml import etree
from xml.etree import ElementTree as ET
from tal.KeywordDrivenBase.Core.ConfigManager import PYTHON_PATH

# Install Appium if not already installed
try:
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy
    from appium.options.common import AppiumOptions
except ImportError:
    os.system(PYTHON_PATH + ' -m pip install Appium-Python-Client')
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy
    from appium.options.common import AppiumOptions

# Install Selenium if not already installed
try:
    from selenium.common.exceptions import WebDriverException, NoSuchElementException, StaleElementReferenceException
    from selenium.webdriver.common.by import By
except ImportError:
    os.system(PYTHON_PATH + ' -m pip install selenium')
    from selenium.common.exceptions import WebDriverException, NoSuchElementException, StaleElementReferenceException
    from selenium.webdriver.common.by import By

# Global variable to store unique element types
ELEMENT_TYPES = set()

class Appium:
    def __init__(self, config_path: str):
        """
        Initializes the mapper with a configuration file path.

        Args:
            config_path (str): Path to the configuration file.

        Raises:
            ValueError: If config_path is empty or invalid.
            FileNotFoundError: If the configuration file does not exist.
            configparser.Error: If the configuration file is invalid or cannot be parsed.
        """
        if not config_path or not isinstance(config_path, str):
            raise ValueError(f"Invalid config_path: '{config_path}' must be a non-empty string")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at '{config_path}'")
        self.config_path = config_path
        self.smartphone_data = self._parse_config_file()

    def _parse_config_file(self) -> Dict[str, Dict[str, str]]:
        """
        Parses the configuration file into a dictionary of sections and key-value pairs, replacing %APP% with the driver directory path.

        Returns:
            Dict[str, Dict[str, str]]: Parsed configuration data.

        Raises:
            ValueError: If the driver directory path cannot be determined.
            FileNotFoundError: If the configuration file does not exist.
            configparser.Error: If the configuration file is invalid or cannot be parsed.
            IOError: If there is an error reading the configuration file.
        """
        try:
            # Determine the driver directory path for %APP% replacement from the config file location
            driver_dir = os.path.dirname(os.path.abspath(self.config_path))
            if not driver_dir or not os.path.isdir(driver_dir):
                raise ValueError(f"Invalid driver directory for %APP% replacement: '{driver_dir}'")

            # Read and preprocess the config file to replace %APP%
            config_content = []
            with open(self.config_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Replace %APP% with driver_dir, preserving path separators
                    processed_line = line.replace("%APP%", driver_dir.replace('\\', os.sep))
                    config_content.append(processed_line)

            # Parse the processed content using configparser
            config = configparser.ConfigParser()
            config.read_string(''.join(config_content))

            data = {}
            for section in config.sections():
                data[section] = {}
                for key, value in config[section].items():
                    data[section][key] = value.strip()

            return data

        except FileNotFoundError as fnf:
            raise FileNotFoundError(f"Failed to read configuration file '{self.config_path}': {fnf}")
        except configparser.Error as ce:
            raise configparser.Error(f"Failed to parse configuration file '{self.config_path}' after %APP% replacement: {ce}")
        except IOError as ioe:
            raise IOError(f"Failed to read configuration file '{self.config_path}': {ioe}")
        except ValueError as ve:
            raise ValueError(f"Failed to parse configuration file '{self.config_path}': {ve}")
        except Exception as e:
            raise Exception(f"Unexpected error while parsing configuration file '{self.config_path}': {e}") from e

    def _get_server_url(self, sp_num: int) -> str:
        """
        Retrieves the Appium server URL for a specified smartphone.

        Args:
            sp_num (int): Smartphone identifier number.

        Returns:
            str: Appium server URL.

        Raises:
            ValueError: If sp_num is invalid or the configuration section is not found.
        """
        try:
            if not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")

            section = f"Smartphone_{sp_num}"
            if section not in self.smartphone_data:
                raise ValueError(f"Configuration section '{section}' not found in '{self.config_path}'")

            return self.smartphone_data[section].get("serverurl", "http://localhost:4723/wd/hub")

        except ValueError as ve:
            raise ValueError(f"Failed to get server URL for Smartphone_{sp_num}: {ve}")

class Mobile:
    def __init__(self, config: dict = None):
        """
        Initializes the Mobile class with an empty devices dictionary.
        """
        self.config_path = None
        self.devices = {}  # Dictionary to store device configurations and drivers

    def LoadPhoneConfiguration(self, path: str) -> None:
        """
        Creates device configurations for all smartphones defined in the config file without initializing drivers.
        """
        try:
            if not path or not isinstance(path, str):
                raise ValueError(f"Invalid configuration path: '{path}' must be a non-empty string")

            config = configparser.ConfigParser()
            config.optionxform = str  # Preserve original case of keys
            if not os.path.exists(path):
                raise FileNotFoundError(f"Configuration file not found at '{path}'")
            config.read(path, encoding="utf-8")

            self.config_path = path

            for section in config.sections():
                if not section.startswith("Smartphone_"):
                    continue
                try:
                    sp_num = int(section.replace("Smartphone_", ""))
                    if sp_num < 0:
                        continue

                    capabilities = dict(config[section])
                    server_url = capabilities.get("appium:serverURL", capabilities.get("serverURL", ""))
                    if not server_url:
                        raise ValueError(f"No serverURL defined for {section}")

                    # Determine platform
                    platform_name = capabilities.get("platformName", capabilities.get("platformname", "")).lower()

                    # Start building always_match for AppiumOptions
                    always_match = {}

                    if platform_name.lower() == "iOS".lower():
                        always_match = {
                            "appium:platformVersion": capabilities.get("platformVersion", capabilities.get("platformversion", "")),
                            "appium:platformName": "iOS",
                            "appium:deviceName": capabilities.get("deviceName", capabilities.get("devicename", "")),
                            "appium:udid": capabilities.get("udid", ""),
                            "appium:automationName": capabilities.get("automationName", capabilities.get("automationname", "XCUITest")),
                            "appium:bundleId": capabilities.get("bundleId", capabilities.get("bundleid", "")),
                            "appium:app": capabilities.get("app", ""),
                            "appium:newCommandTimeout": int(capabilities.get("newCommandTimeout", capabilities.get("newcommandtimeout", 600))),
                            "appium:usePrebuiltWDA": "true"
                        }
                        # Include additional keys from config not already in always_match
                        for key, value in capabilities.items():
                            appium_key = f"appium:{key}" if not key.startswith("appium:") else key
                            if appium_key not in always_match:
                                always_match[appium_key] = value

                    elif platform_name.lower() == "android".lower():
                        # Placeholder for future Android logic
                        always_match = {
                            "appium:platformName": "Android",
                            "appium:platformVersion": capabilities.get("platformVersion", capabilities.get("platformversion", "")),
                            "appium:deviceName": capabilities.get("deviceName", capabilities.get("devicename", "")),
                            "appium:udid": capabilities.get("udid", ""),
                            "appium:automationName": capabilities.get("automationName", capabilities.get("automationname", "UiAutomator2")),
                            "appium:appPackage": capabilities.get("appPackage", capabilities.get("apppackage", "")),
                            "appium:appActivity": capabilities.get("appActivity", capabilities.get("appactivity", "")),
                            "appium:bundleId": capabilities.get("bundleId", capabilities.get("bundleid", "")),
                            "appium:app": capabilities.get("app", ""),
                            "appium:newCommandTimeout": int(capabilities.get("newCommandTimeout", capabilities.get("newcommandtimeout", 600))),
                            "appium:usePrebuiltWDA": "true"
                        }

                    # Build AppiumOptions
                    options = AppiumOptions()
                    options.load_capabilities(always_match)

                    # Initialize device entry if it doesn't exist
                    if sp_num not in self.devices:
                        self.devices[sp_num] = {}

                    # Define the fields to update or add
                    fields_to_update = {
                        "capabilities": capabilities,
                        "server_url": server_url,
                        "options": options,
                        "mapping_path": self._get_mapping_path(sp_num=sp_num)
                    }

                    # Update only if key exists or add new key
                    for key, value in fields_to_update.items():
                        if key in self.devices[sp_num]:
                            self.devices[sp_num][key] = value
                        else:
                            self.devices[sp_num][key] = value

                except ValueError as ve:
                    print(f"Warning: Failed to load configuration for {section}: {ve}")
                    continue

        except FileNotFoundError as fnf:
            raise FileNotFoundError(f"Failed to load configuration file '{path}': {fnf}")
        except configparser.Error as ce:
            raise configparser.Error(f"Failed to parse configuration file '{path}': {ce}")
        except ValueError as ve:
            raise ValueError(f"Failed to load configurations: {ve}")
        except Exception as e:
            raise Exception(f"Unexpected error while loading configuration file '{path}': {e}") from e

    def InitSmartphone(self, alternate_server: str = "", alternate_url: str = "", sp_num: Optional[int] = None) -> bool:
        """
        Initializes or reinitializes the Appium driver for a specific smartphone.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")

            url = alternate_url or alternate_server or self.devices[sp_num]["server_url"]
            if not url or not isinstance(url, str):
                raise ValueError(f"Invalid server URL: '{url}' must be a non-empty string")

            # Reinitialize driver with prebuilt AppiumOptions
            self.devices[sp_num]["driver"] = webdriver.Remote(
                command_executor=url,
                options=self.devices[sp_num]["options"]
            )
            return True

        except WebDriverException as wde:
            raise WebDriverException(f"Failed to initialize Appium driver for Smartphone_{sp_num}: {wde}")
        except ValueError as ve:
            raise ValueError(f"Failed to initialize Appium driver for Smartphone_{sp_num}: {ve}")

    def StartApplication(
        self,
        device_name: str,
        phone_id: str,
        platform_name: str,
        platform_version: str,
        bundle_id: str,
        app_package: str,
        app_activity: str,
        url: str,
        sp_num: Optional[int] = None
    ) -> bool:
        """
        Starts an application on the specified smartphone.

        Args:
            device_name (str): Device name.
            phone_id (str): Device UDID.
            platform_name (str): Platform name (e.g., iOS, Android).
            platform_version (str): Platform version.
            app_package (str): Application package name.
            app_activity (str): Application activity or bundle ID.
            url (str): Appium server URL.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the application starts successfully.

        Raises:
            ValueError: If input parameters are invalid or sp_num is not found.
            WebDriverException: If driver initialization fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not all(isinstance(x, str) and x for x in [device_name, phone_id, platform_name, platform_version, app_package, app_activity, url]):
                raise ValueError("All parameters (device_name, phone_id, platform_name, platform_version, app_package, app_activity, url) must be non-empty strings")

            if platform_name.lower() == "ios":
                capabilities = {
                    "appium:deviceName": device_name,
                    "appium:udid": phone_id,
                    "appium:platformName": platform_name,
                    "appium:platformVersion": platform_version,
                    "appium:automationName": self.devices[sp_num]["capabilities"].get("automationname", "XCUITest"),
                    "appium:bundleId": bundle_id,
                    "appium:newCommandTimeout": self.devices[sp_num]["capabilities"].get("appium:newCommandTimeout", 600),
                    "appium:usePrebuiltWDA": self.devices[sp_num]["capabilities"].get("appium:usePrebuiltWDA", "true")
                }
            elif platform_name.lower() == "android":
                capabilities = {
                    "appium:deviceName": device_name,
                    "appium:udid": phone_id,
                    "appium:platformName": platform_name,
                    "appium:platformVersion": platform_version,
                    "appium:automationName": self.devices[sp_num]["capabilities"].get("automationname", "UiAutomator2"),
                    "appium:appPackage" = app_package
                    "appium:appActivity" = app_activity
                    "appium:newCommandTimeout": self.devices[sp_num]["capabilities"].get("appium:newCommandTimeout", 600),
                    "appium:usePrebuiltWDA": self.devices[sp_num]["capabilities"].get("appium:usePrebuiltWDA", "true")
                }

            options = AppiumOptions()
            options.load_capabilities(capabilities)
            self.devices[sp_num]["driver"] = webdriver.Remote(command_executor=url, options=options)
            return True

        except ValueError as ve:
            raise ValueError(f"Failed to start application for Smartphone_{sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to start application with bundleId '{app_activity}' for Smartphone_{sp_num}: {wde}")

    def GoToWindow(self, target_window: str, sp_num: Optional[int] = None) -> bool:
        """
        Simulates navigation to a specific window or context.

        Args:
            target_window (str): The target window or context identifier.
            sp_num (Optional[int]): Smartphon:e identifier.

        Returns:
            bool: True (simulation placeholder).

        Raises:
            ValueError: If target_window is invalid or sp_num is not found.
            WebDriverException: If driver is not initialized.
        """
        if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
            raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
        if sp_num not in self.devices:
            raise ValueError(f"Device {sp_num} not found in loaded configurations")
        if self.devices[sp_num]["driver"] is None:
            raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
        raise NotImplementedError("Simulated Go To Window (not implemented)")

    def SwipeLeft(self, repeat_count: int, back_interval_ms: float, sp_num: Optional[int] = None) -> bool:
        """
        Performs left swipe gestures on the specified smartphone.

        Args:
            repeat_count (int): Number of swipes to perform.
            back_interval_ms (float): Delay between swipes in milliseconds.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if swipes are successful.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If the swipe operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not isinstance(repeat_count, int) or repeat_count < 0:
                raise ValueError(f"Invalid repeat_count: {repeat_count} must be a non-negative integer")
            if not isinstance(back_interval_ms, (int, float)) or back_interval_ms < 0:
                raise ValueError(f"Invalid back_interval_ms: {back_interval_ms} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            for _ in range(repeat_count):
                self.devices[sp_num]["driver"].swipe(550, 500, 450, 500, 300)
                time.sleep(back_interval_ms / 1000.0)
            return True

        except ValueError as ve:
            raise ValueError(f"Failed to perform left swipe for Smartphone_{sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to perform left swipe with repeat_count={repeat_count} for Smartphone_{sp_num}: {wde}")

    def SwipeRight(self, repeat_count: int, back_interval_ms: float, sp_num: Optional[int] = None) -> bool:
        """
        Performs right swipe gestures on the specified smartphone.

        Args:
            repeat_count (int): Number of swipes to perform.
            back_interval_ms (float): Delay between swipes in milliseconds.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if swipes are successful.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If the swipe operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not isinstance(repeat_count, int) or repeat_count < 0:
                raise ValueError(f"Invalid repeat_count: {repeat_count} must be a non-negative integer")
            if not isinstance(back_interval_ms, (int, float)) or back_interval_ms < 0:
                raise ValueError(f"Invalid back_interval_ms: {back_interval_ms} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            for _ in range(repeat_count):
                self.devices[sp_num]["driver"].swipe(450, 500, 550, 500, 300)
                time.sleep(back_interval_ms / 1000.0)
            return True

        except ValueError as ve:
            raise ValueError(f"Failed to perform right swipe for Smartphone_{sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to perform right swipe with repeat_count={repeat_count} for Smartphone_{sp_num}: {wde}")

    def SwipeUp(self, swipe_count: int, interval_ms: float, sp_num: Optional[int] = None) -> bool:
        """
        Performs upward swipe gestures on the specified smartphone.

        Args:
            swipe_count (int): Number of swipes to perform.
            interval_ms (float): Delay between swipes in milliseconds.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if swipes are successful.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If the swipe operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not isinstance(swipe_count, int) or swipe_count < 0:
                raise ValueError(f"Invalid swipe_count: {swipe_count} must be a non-negative integer")
            if not isinstance(interval_ms, (int, float)) or interval_ms < 0:
                raise ValueError(f"Invalid interval_ms: {interval_ms} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            for _ in range(swipe_count):
                self.devices[sp_num]["driver"].swipe(500, 550, 500, 450, 300)
                time.sleep(interval_ms / 1000.0)
            return True

        except ValueError as ve:
            raise ValueError(f"Failed to perform upward swipe for Smartphone_{sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to perform upward swipe with swipe_count={swipe_count} for Smartphone_{sp_num}: {wde}")

    def SwipeDown(self, swipe_count: int, interval_ms: float, sp_num: Optional[int] = None) -> bool:
        """
        Performs downward swipe gestures on the specified smartphone.

        Args:
            swipe_count (int): Number of swipes to perform.
            interval_ms (float): Delay between swipes in milliseconds.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if swipes are successful.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If the swipe operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not isinstance(swipe_count, int) or swipe_count < 0:
                raise ValueError(f"Invalid swipe_count: {swipe_count} must be a non-negative integer")
            if not isinstance(interval_ms, (int, float)) or interval_ms < 0:
                raise ValueError(f"Invalid interval_ms: {interval_ms} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            for _ in range(swipe_count):
                self.devices[sp_num]["driver"].swipe(500, 450, 500, 550, 300)
                time.sleep(interval_ms / 1000.0)
            return True

        except ValueError as ve:
            raise ValueError(f"Failed to perform downward swipe for Smartphone_{sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to perform downward swipe with swipe_count={swipe_count} for Smartphone_{sp_num}: {wde}")

    def SetElementText(self, element: str, text: str, append: bool, sp_num: Optional[int] = None) -> bool:
        """
        Sets the text of an element on the specified smartphone, optionally appending to existing text.

        Args:
            element (str): The logical name of the element or an XPath expression.
            text (str): The text to set.
            append (bool): If True, appends text; if False, clears before setting.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the text is set successfully.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is not found.
            AssertionError: If the element is not visible or enabled for text input.
            etree.LxmlError: If the XML source is invalid.
            WebDriverException: If there is an issue with the WebDriver during text setting.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not isinstance(text, str):
                raise ValueError(f"Invalid text: '{text}' must be a string")
            if not isinstance(append, bool):
                raise ValueError(f"Invalid append: {append} must be a boolean")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            xpath = None
            xml_source = self.devices[sp_num]["driver"].page_source
            self.mapping_path = self.devices[sp_num]["mapping_path"]
            elem = None
            text_to_find = element

            # Check if the element is an XPath (starts with /)
            if element.startswith("/"):
                xpath = element
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            if xpath is not None:
                # Use the provided or resolved XPath to get the element
                elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # Fallback to finding the deepest matching element by text
            if elem is None:
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                if match is not None:
                    elem = match["element"]
                    # Construct XPath from the found element
                    xpath = self._element_to_xpath(elem)
                    if xpath is None:
                        raise ValueError(f"Could not construct XPath for element '{element}'")
                    # Re-fetch element with constructed XPath for consistency
                    elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # If no element is found, raise an exception
            if elem is None:
                raise ValueError(f"No element found for '{element}' in XML source")

            # Check if the element is visible and enabled
            is_visible = self._is_element_visible(elem, sp_num=sp_num)
            is_enabled = elem.attrib.get("enabled", "false").lower() == "true"
            if not (is_visible and is_enabled):
                raise AssertionError(f"Element '{element}' is not editable (visible={is_visible}, enabled={is_enabled})")

            # Fetch WebDriver element for text operations
            webdriver_elem = self.devices[sp_num]["driver"].find_element(AppiumBy.XPATH, xpath)
            if not append:
                webdriver_elem.clear()
            webdriver_elem.send_keys(text)
            return True

        except AssertionError:
            raise  # Re-raise AssertionError without wrapping
        except ValueError as ve:
            raise ValueError(f"Failed to set text for element '{element}' on Smartphone_{sp_num}: {ve}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to set text for element '{element}' on Smartphone_{sp_num} due to XML parsing: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to set text for element '{element}' with XPath '{xpath}' on Smartphone_{sp_num}: {wde}")

    def GoBack(self, repeat_count: int, back_interval_ms: float, sp_num: Optional[int] = None) -> bool:
        """
        Performs back navigation on the specified smartphone.

        Args:
            repeat_count (int): Number of back actions to perform.
            back_interval_ms (float): Delay between back actions in milliseconds.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if back actions are successful.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If the back operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not isinstance(repeat_count, int) or repeat_count < 0:
                raise ValueError(f"Invalid repeat_count: {repeat_count} must be a non-negative integer")
            if not isinstance(back_interval_ms, (int, float)) or back_interval_ms < 0:
                raise ValueError(f"Invalid back_interval_ms: {back_interval_ms} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            for _ in range(repeat_count):
                self.devices[sp_num]["driver"].back()
                time.sleep(back_interval_ms / 1000.0)
            return True

        except ValueError as ve:
            raise ValueError(f"Failed to perform back navigation for Smartphone_{sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to perform back navigation with repeat_count={repeat_count} for Smartphone_{sp_num}: {wde}")

    def EnableBLE(self, sp_num: Optional[int] = None) -> bool:
        """
        Simulates enabling Bluetooth Low Energy on the specified smartphone (not implemented).

        Args:
            sp_num (Optional[int]): Smartphone identifier.

        Raises:
            ValueError: If sp_num is invalid or not found.
            NotImplementedError: Always raised as the method is not implemented.
        """
        if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
            raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
        if sp_num not in self.devices:
            raise ValueError(f"Device {sp_num} not found in loaded configurations")
        if self.devices[sp_num]["driver"] is None:
            raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
        raise NotImplementedError("Simulated enabling BLE (not implemented)")

    def DisableBLE(self, sp_num: Optional[int] = None) -> bool:
        """
        Simulates disabling Bluetooth Low Energy on the specified smartphone (not implemented).

        Args:
            sp_num (Optional[int]): Smartphone identifier.

        Raises:
            ValueError: If sp_num is invalid or not found.
            NotImplementedError: Always raised as the method is not implemented.
        """
        if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
            raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
        if sp_num not in self.devices:
            raise ValueError(f"Device {sp_num} not found in loaded configurations")
        if self.devices[sp_num]["driver"] is None:
            raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
        raise NotImplementedError("Simulated disabling BLE (not implemented)")

    def ShowNotificationControlPanel(self, sp_num: Optional[int] = None) -> bool:
        """
        Shows the notification control panel on the specified smartphone by swiping down and verifying a Bluetooth button.

        Args:
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the panel is shown and the Bluetooth button is visible.

        Raises:
            ValueError: If screen dimensions are invalid or sp_num is not found.
            WebDriverException: If the swipe or element lookup fails.
            TimeoutError: If the Bluetooth button is not visible within 5 seconds.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            size = self.devices[sp_num]["driver"].get_window_size()
            if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                raise ValueError("Invalid screen dimensions returned by driver")

            self.mapping_path = self.devices[sp_num]["mapping_path"]
            start_x = size['width'] - 10
            start_y = 10
            end_y = size['height'] // 2
            self.devices[sp_num]["driver"].swipe(start_x, start_y, start_x, end_y, 400)

            # Check if BLE_Indicator is present and non-empty
            ble_indicator = self._get_capability(sp_num, 'BLE_Indicator')
            if not ble_indicator:
                return True  # Bypass check if BLE_Indicator is absent or empty

            # Initialize XPath
            xpath = None
            if ble_indicator.startswith("/"):
                xpath = ble_indicator
            else:
                xpath = self._resolve_xpath(ble_indicator)

            if not xpath:
                raise ValueError(f"Invalid XPath resolved from BLE_Indicator: '{ble_indicator}'")

            # Normalize XPath quotes and create variations
            normalized_xpath = re.sub(r"@(\w+)=[']([^']*?)[']", r'@\1="\2"', xpath)
            xpath_variations = [
                xpath,
                normalized_xpath,
                re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[normalize-space(.)="\2"]', normalized_xpath),
                re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[contains(., "\2")]', normalized_xpath)
            ]

            end_time = time.time() + 5
            while time.time() < end_time:
                xml_source = self.devices[sp_num]["driver"].page_source
                for alt_xpath in xpath_variations:
                    try:
                        # Check element presence in XML
                        elem = self._get_element_from_xpath(xml=xml_source, xpath=alt_xpath)
                        if elem is None:
                            return True  # Element not found, considered not visible
                        # Check if element is visible
                        is_visible = self._is_element_visible(elem, sp_num=sp_num)
                        if not is_visible:
                            return True  # Element not visible
                    except (NoSuchElementException, etree.LxmlError):
                        return True  # Element not found or XML error, considered not visible
                time.sleep(0.3)

            raise TimeoutError("Timeout after 5s: Bluetooth indicator still visible in notification control panel")

        except ValueError as ve:
            raise ValueError(f"Failed to check Bluetooth indicator for Smartphone_{sp_num}: {ve}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to parse XML for Bluetooth indicator check for Smartphone_{sp_num}: {le}")
        except TimeoutError:
            raise  # Re-raise TimeoutError

    def HideNotificationControlPanel(self, sp_num: Optional[int] = None) -> bool:
        """
        Hides the notification control panel on the specified smartphone by swiping up and verifying the Bluetooth button is not visible.

        Args:
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the panel is hidden.

        Raises:
            ValueError: If screen dimensions are invalid or sp_num is not found.
            WebDriverException: If the swipe operation fails.
            TimeoutError: If the Bluetooth button remains visible after 5 seconds.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            size = self.devices[sp_num]["driver"].get_window_size()
            if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                raise ValueError("Invalid screen dimensions returned by driver")

            self.mapping_path = self.devices[sp_num]["mapping_path"]
            start_x = size['width'] // 2
            start_y = size['height'] - 100
            end_y = 100
            self.devices[sp_num]["driver"].swipe(start_x, start_y, start_x, end_y, 400)

            # Check if BLE_Indicator is present and non-empty
            ble_indicator = self._get_capability(sp_num, 'BLE_Indicator')
            if not ble_indicator:
                return True  # Bypass check if BLE_Indicator is absent or empty

            # Initialize XPath
            xpath = None
            if ble_indicator.startswith("/"):
                xpath = ble_indicator
            else:
                xpath = self._resolve_xpath(ble_indicator)

            if not xpath:
                raise ValueError(f"Invalid XPath resolved from BLE_Indicator: '{ble_indicator}'")

            # Normalize XPath quotes and create variations
            normalized_xpath = re.sub(r"@(\w+)=[']([^']*?)[']", r'@\1="\2"', xpath)
            xpath_variations = [
                xpath,
                normalized_xpath,
                re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[normalize-space(.)="\2"]', normalized_xpath),
                re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[contains(., "\2")]', normalized_xpath)
            ]

            end_time = time.time() + 5
            while time.time() < end_time:
                xml_source = self.devices[sp_num]["driver"].page_source
                for alt_xpath in xpath_variations:
                    try:
                        # Check element presence in XML
                        elem = self._get_element_from_xpath(xml=xml_source, xpath=alt_xpath)
                        if elem is None:
                            return True  # Element not found, considered not visible
                        # Check if element is visible
                        is_visible = self._is_element_visible(elem, sp_num=sp_num)
                        if not is_visible:
                            return True  # Element not visible
                    except (NoSuchElementException, etree.LxmlError):
                        return True  # Element not found or XML error, considered not visible
                time.sleep(0.3)

            raise TimeoutError("Timeout after 5s: Bluetooth indicator still visible in notification control panel")

        except ValueError as ve:
            raise ValueError(f"Failed to check Bluetooth indicator for Smartphone_{sp_num}: {ve}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to parse XML for Bluetooth indicator check for Smartphone_{sp_num}: {le}")
        except TimeoutError:
            raise  # Re-raise TimeoutError

    def UnlockDevice(self, sp_num: Optional[int] = None) -> bool:
        """
        Unlocks the specified smartphone.

        Args:
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the device is unlocked successfully.

        Raises:
            ValueError: If sp_num is invalid or not found.
            WebDriverException: If the unlock operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
            self.devices[sp_num]["driver"].unlock()
            return True
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to unlock device for Smartphone_{sp_num}: {wde}")
        except ValueError as ve:
            raise ValueError(f"Failed to unlock device for Smartphone_{sp_num}: {ve}")

    def LockDevice(self, sp_num: Optional[int] = None) -> bool:
        """
        Locks the specified smartphone.

        Args:
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the device is locked successfully.

        Raises:
            ValueError: If sp_num is invalid or not found.
            WebDriverException: If the lock operation fails.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
            self.devices[sp_num]["driver"].lock()
            return True
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to lock device for Smartphone_{sp_num}: {wde}")
        except ValueError as ve:
            raise ValueError(f"Failed to lock device for Smartphone_{sp_num}: {ve}")

    def CheckTextPresence(self, name_substring: str, sp_num: Optional[int] = None, scroll_distance: int = 50, timeout: int = 8000) -> bool:
        """
        Checks if an element containing the specified substring is present in the XML page source of the specified smartphone.

        Args:
            name_substring (str): The substring to search for in element text or attributes.
            sp_num (Optional[int]): Smartphone identifier.
            scroll_distance (int): Distance to scroll in pixels when adjusting view (default: 50).
            timeout (int): Maximum time to wait for the element in milliseconds (default: 8000).

        Returns:
            bool: True if an element matching the substring is found within the timeout.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If there's an issue with the WebDriver interaction.
            etree.LxmlError: If the XML page source is invalid.
            TimeoutError: If the timeout expires without finding the element.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not name_substring or not isinstance(name_substring, str):
                raise ValueError(f"Invalid name_substring: '{name_substring}' must be a non-empty string")
            if not isinstance(scroll_distance, int) or scroll_distance <= 0:
                raise ValueError(f"Invalid scroll_distance: {scroll_distance} must be positive")
            if not isinstance(timeout, int) or timeout < 0:
                raise ValueError(f"Invalid timeout: {timeout} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            # Get screen dimensions
            window_size = self.devices[sp_num]["driver"].get_window_size()
            if not isinstance(window_size, dict) or 'width' not in window_size or 'height' not in window_size:
                raise WebDriverException("Failed to retrieve valid window size from driver")
            screen_width = window_size['width']
            screen_height = window_size['height']

            # Define thresholds (10% of screen height)
            threshold = screen_height * 0.1
            top_threshold = threshold
            bottom_threshold = screen_height - threshold

            # Timeout and polling setup
            start_time = time.time()
            timeout_seconds = timeout / 1000.0
            poll_interval = 0.5  # seconds

            while (time.time() - start_time) < timeout_seconds:
                # Get page source
                xml_source = self.devices[sp_num]["driver"].page_source
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=name_substring, sp_num=sp_num)
                if match:
                    element, x, y = match["element"], match["x"], match["y"]

                    # Check if scrolling is needed
                    scrolled = False
                    center_x = screen_width // 2
                    if y < top_threshold or y < 0:
                        # Swipe down to bring element into view
                        start_y = int(screen_height * 0.3)
                        end_y = start_y + scroll_distance
                        self.devices[sp_num]["driver"].swipe(center_x, start_y, center_x, end_y, 300)
                        scrolled = True
                    elif y > bottom_threshold or y > screen_height:
                        # Swipe up to bring element into view
                        start_y = int(screen_height * 0.7)
                        end_y = start_y - scroll_distance
                        self.devices[sp_num]["driver"].swipe(center_x, start_y, center_x, end_y, 300)
                        scrolled = True

                    if scrolled:
                        # Re-fetch page source and re-find element
                        xml_source = self.devices[sp_num]["driver"].page_source
                        match = self._get_deepest_matching_element(xml=xml_source, text_to_find=name_substring, sp_num=sp_num)
                        if not match:
                            continue  # Element not found after scrolling, try again
                        element, x, y = match["element"], match["x"], match["y"]

                    # Verify final coordinates
                    if x < 0 or x > screen_width or y < 0 or y > screen_height:
                        continue  # Skip invalid coordinates, try again

                    return True  # Element found

                time.sleep(poll_interval)

            print(
                f"Timeout after {timeout}ms: No element found matching '{name_substring}' for Smartphone_{sp_num}"
            )
            return False
        
        except WebDriverException as wde:
            raise WebDriverException(
                f"Failed to check presence of substring '{name_substring}' for Smartphone_{sp_num}: WebDriver error. Error: {wde}"
            )
        except etree.LxmlError as le:
            raise etree.LxmlError(
                f"Failed to check presence of substring '{name_substring}' for Smartphone_{sp_num}: Invalid XML source. Error: {le}"
            )

    def TapByScreenCoverageFromSubString(
        self,
        name_substring: str,
        tap_count: int,
        tap_duration_ms: int = 100,
        sp_num: Optional[int] = None,
        scroll_distance: int = 50,
        timeout: int = 8000,
        scroll_if_needed: bool = False
    ) -> bool:
        """
        Taps an element identified by a substring using screen coordinates on the specified smartphone.
        Optionally scrolls the screen downward to find the element if it is not initially visible.

        Args:
            name_substring (str): The substring to search for in element text or attributes.
            tap_count (int): Number of times to tap the element.
            tap_duration_ms (int): Duration of each tap in milliseconds (default: 100).
            sp_num (Optional[int]): Smartphone identifier.
            scroll_distance (int): Distance to scroll in pixels when adjusting view (default: 50).
            timeout (int): Maximum time to wait for the element in milliseconds (default: 8000).
            scroll_if_needed (bool): If True, attempts to scroll down repeatedly until the element is found
                                    or until the end of the scrollable content is reached (default: False).

        Returns:
            bool: True if the tap(s) were successful.

        Raises:
            ValueError: If inputs are invalid or sp_num is not found.
            WebDriverException: If there's an issue with the WebDriver interaction.
            etree.LxmlError: If the XML page source is invalid.
            TimeoutError: If the timeout expires without finding the element.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not name_substring or not isinstance(name_substring, str):
                raise ValueError(f"Invalid name_substring: '{name_substring}' must be a non-empty string")
            if not isinstance(tap_count, int) or tap_count < 0:
                raise ValueError(f"Invalid tap_count: {tap_count} must be non-negative")
            if not isinstance(tap_duration_ms, int) or tap_duration_ms < 0:
                raise ValueError(f"Invalid tap_duration_ms: {tap_duration_ms} must be non-negative")
            if not isinstance(scroll_distance, int) or scroll_distance <= 0:
                raise ValueError(f"Invalid scroll_distance: {scroll_distance} must be positive")
            if not isinstance(timeout, int) or timeout < 0:
                raise ValueError(f"Invalid timeout: {timeout} must be non-negative")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            platform_name = self.devices[sp_num]["capabilities"].get(
                "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
            ).lower()

            # Get screen dimensions
            window_size = self.devices[sp_num]["driver"].get_window_size()
            if not isinstance(window_size, dict) or 'width' not in window_size or 'height' not in window_size:
                raise WebDriverException("Failed to retrieve valid window size from driver")
            screen_width = window_size['width']
            screen_height = window_size['height']

            # Define thresholds (10% of screen height)
            threshold = screen_height * 0.1
            top_threshold = threshold
            bottom_threshold = screen_height - threshold

            # Timeout and polling setup
            start_time = time.time()
            timeout_seconds = timeout / 1000.0
            poll_interval = 0.5  # seconds

            last_page_source = ""
            while (time.time() - start_time) < timeout_seconds:
                # Get current page source
                xml_source = self.devices[sp_num]["driver"].page_source

                # Try to find the element
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=name_substring, sp_num=sp_num)
                if match:
                    element, x, y = match["element"], match["x"], match["y"]

                    # Check if scrolling is needed to bring it into view
                    scrolled = False
                    center_x = screen_width // 2
                    if scroll_if_needed:
                        if y < top_threshold or y < 0:
                            start_y = int(screen_height * 0.3)
                            end_y = start_y + scroll_distance
                            self.devices[sp_num]["driver"].swipe(center_x, start_y, center_x, end_y, 300)
                            scrolled = True
                        elif y > bottom_threshold or y > screen_height:
                            start_y = int(screen_height * 0.7)
                            end_y = start_y - scroll_distance
                            self.devices[sp_num]["driver"].swipe(center_x, start_y, center_x, end_y, 300)
                            scrolled = True

                    if scrolled:
                        xml_source = self.devices[sp_num]["driver"].page_source
                        match = self._get_deepest_matching_element(xml=xml_source, text_to_find=name_substring, sp_num=sp_num)
                        if not match:
                            continue  # Still not found, keep looping
                        element, x, y = match["element"], match["x"], match["y"]

                    # Ensure the coordinates are valid
                    if x < 0 or x > screen_width or y < 0 or y > screen_height:
                        raise ValueError(
                            f"Failed to tap '{name_substring}' for Smartphone_{sp_num}: Coordinates (x={x}, y={y}) "
                            f"are outside screen range (width={screen_width}, height={screen_height})"
                        )

                    # Perform tap(s)
                    for _ in range(tap_count):
                        if platform_name.lower() == "iOS".lower():
                            self._tap_gesture_iOS(x, y, duration=100, sp_num=sp_num)
                        elif platform_name.lower() == "android".lower():
                            self._tap_gesture_android(x, y, duration=100, sp_num=sp_num)
                    return True

                if scroll_if_needed:
                    # Stop if page content doesn’t change — reached bottom
                    if xml_source == last_page_source:
                        break
                    last_page_source = xml_source

                    # Try scrolling down
                    center_x = screen_width // 2
                    start_y = int(screen_height * 0.7)
                    end_y = start_y - scroll_distance
                    self.devices[sp_num]["driver"].swipe(center_x, start_y, center_x, end_y, 300)

                time.sleep(poll_interval)

            print(
                f"Timeout after {timeout}ms: No element found matching element '{name_substring}' for Smartphone_{sp_num}"
            )
            return False

        except WebDriverException as wde:
            raise WebDriverException(
                f"Failed to tap '{name_substring}' by screen coverage with tap_count={tap_count}, "
                f"duration={tap_duration_ms}ms for Smartphone_{sp_num}: WebDriver error. Error: {wde}"
            )
        except etree.LxmlError as le:
            raise etree.LxmlError(
                f"Failed to tap '{name_substring}' by screen coverage for Smartphone_{sp_num}: Invalid XML source. Error: {le}"
            )

    def TapElement(self, name: str, sp_num: Optional[int] = None) -> bool:
        """
        Taps an element on the specified smartphone using XPath, text-based fallback, or screen coverage tap.

        Args:
            name (str): The logical name of the element or an XPath expression.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the tap is successful.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, coordinates are invalid, or sp_num is not found.
            AssertionError: If the element is not visible or enabled for tapping.
            etree.LxmlError: If the XML source is invalid.
            TimeoutError: If the element is not found after attempting all fallbacks.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not name or not isinstance(name, str):
                raise ValueError(f"Invalid name: '{name}' must be a non-empty string")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
            
            platform_name = self.devices[sp_num]["capabilities"].get(
                "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
            ).lower()

            xpath = None
            xml_source = self.devices[sp_num]["driver"].page_source
            self.mapping_path = self.devices[sp_num]["mapping_path"]
            elem = None
            text_to_find = name
            fallback_coordinates = None

            # Check if the name is an XPath (starts with /)
            if name.startswith("/"):
                xpath = name
                # Extract name value for fallback
                match = re.search(r"@(name|label|value)=['\"]([^'\"]*?)['\"]", name)
                if match:
                    text_to_find = match.group(2).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(name)

            if xpath is not None:
                # Normalize XPath quotes and try variations
                normalized_xpath = re.sub(r"@(\w+)=[']([^']*?)[']", r'@\1="\2"', xpath)
                xpath_variations = [
                    xpath,
                    normalized_xpath,
                    re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[normalize-space(.)="\2"]', normalized_xpath),
                    re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[contains(., "\2")]', normalized_xpath)
                ]
                for alt_xpath in xpath_variations:
                    try:
                        # Use _get_element_from_xpath for state validation
                        elem = self._get_element_from_xpath(xml=xml_source, xpath=alt_xpath)
                        if elem is not None:
                            # Check if the element is visible and enabled
                            is_visible = self._is_element_visible(elem, sp_num=sp_num)
                            is_enabled = elem.attrib.get("enabled", "false").lower() == "true"
                            if not (is_visible and is_enabled):
                                raise AssertionError(f"Element '{name}' is not tappable (visible={is_visible}, enabled={is_enabled})")
                            # Store initial coordinates as fallback
                            try:
                                # Parse width and height, default to 0 if missing or invalid
                                try:
                                    if platform_name.lower() == "iOS".lower():
                                        width, height = self._parse_size_iOS(elem)
                                    elif platform_name.lower() == "android".lower():
                                        width, height = self._parse_size_android(elem)
                                except (TypeError, ValueError):
                                    width = 0
                                    height = 0

                                # Parse x and y coordinates, default to -1 if missing or invalid
                                try:
                                    if platform_name.lower() == "iOS".lower():
                                        x, y = self._parse_position_iOS(elem)
                                    elif platform_name.lower() == "android".lower():
                                        x, y = self._parse_size_android(elem)
                                except (TypeError, ValueError):
                                    x = -1
                                    y = -1
                                
                                # x = int(elem.attrib.get("x", "-1"))
                                # y = int(elem.attrib.get("y", "-1"))
                                # width = int(elem.attrib.get("width", "0"))
                                # height = int(elem.attrib.get("height", "0"))
                                center_x = x + width / 2
                                center_y = y + height / 2
                                size = self.devices[sp_num]["driver"].get_window_size()
                                if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                                    raise ValueError("Invalid screen dimensions returned by driver")
                                if center_x >= 0 and center_x <= size['width'] and center_y >= 0 and center_y <= size['height']:
                                    fallback_coordinates = (center_x, center_y)
                            except ValueError:
                                pass  # Continue without fallback coordinates if invalid
                            # Fetch WebDriver element and tap
                            try:
                                webdriver_elem = self.devices[sp_num]["driver"].find_element(AppiumBy.XPATH, alt_xpath)
                                self._tap_element_center(webdriver_elem, sp_num=sp_num)
                            except (NoSuchElementException, StaleElementReferenceException, ValueError):
                                # Try fallback coordinates if available
                                if fallback_coordinates:
                                    center_x, center_y = fallback_coordinates
                                    if platform_name.lower() == "iOS".lower():
                                        self._tap_gesture_iOS(center_x, center_y, duration=100, sp_num=sp_num)
                                    elif platform_name.lower() == "android".lower():
                                        self._tap_gesture_android(center_x, center_y, duration=100, sp_num=sp_num)
                                else:
                                    continue  # Try next XPath variation
                            return True
                    except (NoSuchElementException, StaleElementReferenceException, ValueError):
                        continue  # Try next XPath variation

            # Fallback to finding the deepest matching element by text
            match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
            if match is not None:
                elem = match["element"]
                # Check if the element is visible and enabled
                is_visible = self._is_element_visible(elem, sp_num=sp_num)
                is_enabled = elem.attrib.get("enabled", "false").lower() == "true"
                if not (is_visible and is_enabled):
                    raise AssertionError(f"Element '{name}' is not tappable (visible={is_visible}, enabled={is_enabled})")
                # Construct XPath from the found element
                xpath = self._element_to_xpath(elem)
                if xpath is None:
                    raise ValueError(f"Could not construct XPath for element '{name}'")
                # Use coordinates for tapping
                x, y = match["x"], match["y"]
                size = self.devices[sp_num]["driver"].get_window_size()
                if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                    raise ValueError("Invalid screen dimensions returned by driver")
                if x < 0 or x > size['width'] or y < 0 or y > size['height']:
                    raise ValueError(
                        f"Failed to tap '{name}' for Smartphone_{sp_num}: Coordinates (x={x}, y={y}) are outside "
                        f"screen range (width={size['width']}, height={size['height']})"
                    )
                if platform_name.lower() == "iOS".lower():
                    self._tap_gesture_iOS(x, y, duration=100, sp_num=sp_num)
                elif platform_name.lower() == "android".lower():
                    self._tap_gesture_android(x, y, duration=100, sp_num=sp_num)
                return True

            # Fallback to TapByScreenCoverageFromSubString
            if not self.TapByScreenCoverageFromSubString(name, tap_count=1, tap_duration_ms=100, sp_num=sp_num):
                print(
                    f"Failed to tap element '{name}' for Smartphone_{sp_num}: XPath not found, text-based search failed, "
                    "and tap by screen coverage failed"
                )
                return False
            return True

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to tap element '{name}' for Smartphone_{sp_num} with text search: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to tap element '{name}' for Smartphone_{sp_num} with text search: {wde}")

    def TapElementExt(self, element_name: str, tap_count: int, delay_between_tap_ms: int, sp_num: Optional[int] = None) -> bool:
        """
        Taps an element multiple times with a specified delay on the specified smartphone using Appium 2.x.

        Args:
            element_name (str): The logical name of the element or an XPath expression.
            tap_count (int): Number of times to tap the element.
            delay_between_tap_ms (int): Delay between taps in milliseconds.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the taps are successful.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, coordinates are invalid, or sp_num is not found.
            AssertionError: If the element is not visible or enabled for tapping.
            etree.LxmlError: If the XML source is invalid.
            TimeoutError: If the element is not found after attempting all fallbacks.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not element_name or not isinstance(element_name, str):
                raise ValueError(f"Invalid element_name: '{element_name}' must be a non-empty string")
            if not isinstance(tap_count, int) or tap_count < 0:
                raise ValueError(f"Invalid tap_count: {tap_count} must be a non-negative integer")
            if not isinstance(delay_between_tap_ms, int) or delay_between_tap_ms < 0:
                raise ValueError(f"Invalid delay_between_tap_ms: {delay_between_tap_ms} must be a non-negative integer")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")

            platform_name = self.devices[sp_num]["capabilities"].get(
                "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
            ).lower()

            xpath = None
            xml_source = self.devices[sp_num]["driver"].page_source
            self.mapping_path = self.devices[sp_num]["mapping_path"]
            elem = None
            text_to_find = element_name
            fallback_coordinates = None

            # Check if the element_name is an XPath (starts with /)
            if element_name.startswith("/"):
                xpath = element_name
                # Extract name value for fallback
                match = re.search(r"@(name|label|value)=['\"]([^'\"]*?)['\"]", element_name)
                if match:
                    text_to_find = match.group(2).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element_name)

            if xpath is not None:
                # Normalize XPath quotes and try variations
                normalized_xpath = re.sub(r"@(\w+)=[']([^']*?)[']", r'@\1="\2"', xpath)
                xpath_variations = [
                    xpath,
                    normalized_xpath,
                    re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[normalize-space(.)="\2"]', normalized_xpath),
                    re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[contains(., "\2")]', normalized_xpath)
                ]
                for alt_xpath in xpath_variations:
                    for _ in range(2):  # Retry twice
                        try:
                            # Use _get_element_from_xpath for state validation
                            elem = self._get_element_from_xpath(xml=xml_source, xpath=alt_xpath)
                            if elem is not None:
                                # Check if the element is visible and enabled
                                is_visible = self._is_element_visible(elem, sp_num=sp_num)
                                is_enabled = elem.attrib.get("enabled", "false").lower() == "true"
                                if not (is_visible and is_enabled):
                                    raise AssertionError(f"Element '{element_name}' is not tappable (visible={is_visible}, enabled={is_enabled})")
                                # Store initial coordinates as fallback
                                try:
                                    # Parse width and height, default to 0 if missing or invalid
                                    try:
                                        if platform_name.lower() == "iOS".lower():
                                            width, height = self._parse_size_iOS(elem)
                                        elif platform_name.lower() == "android".lower():
                                            width, height = self._parse_size_android(elem)
                                    except (TypeError, ValueError):
                                        width = 0
                                        height = 0

                                    # Parse x and y coordinates, default to -1 if missing or invalid
                                    try:
                                        if platform_name.lower() == "iOS".lower():
                                            x, y = self._parse_position_iOS(elem)
                                        elif platform_name.lower() == "android".lower():
                                            x, y = self._parse_size_android(elem)
                                    except (TypeError, ValueError):
                                        x = -1
                                        y = -1
                                    # x = int(elem.attrib.get("x", "-1"))
                                    # y = int(elem.attrib.get("y", "-1"))
                                    # width = int(elem.attrib.get("width", "0"))
                                    # height = int(elem.attrib.get("height", "0"))
                                    center_x = x + width / 2
                                    center_y = y + height / 2
                                    size = self.devices[sp_num]["driver"].get_window_size()
                                    if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                                        raise ValueError("Invalid screen dimensions returned by driver")
                                    if center_x >= 0 and center_x <= size['width'] and center_y >= 0 and center_y <= size['height']:
                                        fallback_coordinates = (center_x, center_y)
                                except ValueError:
                                    pass  # Continue without fallback coordinates if invalid
                                # Tap the element multiple times, re-fetching each time
                                for i in range(tap_count):
                                    try:
                                        webdriver_elem = self.devices[sp_num]["driver"].find_element(AppiumBy.XPATH, alt_xpath)
                                        self._tap_element_center(webdriver_elem, sp_num=sp_num)
                                    except (NoSuchElementException, StaleElementReferenceException, ValueError):
                                        # Try fallback coordinates if available
                                        if fallback_coordinates:
                                            center_x, center_y = fallback_coordinates
                                            if platform_name.lower() == "iOS".lower():
                                                self._tap_gesture_iOS(center_x, center_y, duration=100, sp_num=sp_num)
                                            elif platform_name.lower() == "android".lower():
                                                self._tap_gesture_android(center_x, center_y, duration=100, sp_num=sp_num)
                                        else:
                                            raise ValueError(f"Failed to tap '{element_name}' after retrying with XPath '{alt_xpath}'")
                                    if i < tap_count - 1:
                                        time.sleep(delay_between_tap_ms / 1000.0)
                                        xml_source = self.devices[sp_num]["driver"].page_source  # Refresh XML source for next tap
                                return True
                        except (NoSuchElementException, WebDriverException, StaleElementReferenceException):
                            # Refresh XML source and retry
                            xml_source = self.devices[sp_num]["driver"].page_source
                            continue
                        break  # Exit retry loop if successful

            # Fallback to finding the deepest matching element by text
            match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
            if match is not None:
                elem = match["element"]
                # Check if the element is visible and enabled
                is_visible = self._is_element_visible(elem, sp_num=sp_num)
                is_enabled = elem.attrib.get("enabled", "false").lower() == "true"
                if not (is_visible and is_enabled):
                    raise AssertionError(f"Element '{element_name}' is not tappable (visible={is_visible}, enabled={is_enabled})")
                # Construct XPath from the found element
                xpath = self._element_to_xpath(elem)
                if xpath is None:
                    raise ValueError(f"Could not construct XPath for element '{element_name}'")
                # Use coordinates for tapping
                x, y = match["x"], match["y"]
                size = self.devices[sp_num]["driver"].get_window_size()
                if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                    raise ValueError("Invalid screen dimensions returned by driver")
                if x < 0 or x > size['width'] or y < 0 or y > size['height']:
                    raise ValueError(
                        f"Failed to tap '{element_name}' for Smartphone_{sp_num}: Coordinates (x={x}, y={y}) are outside "
                        f"screen range (width={size['width']}, height={size['height']})"
                    )
                for i in range(tap_count):
                    if platform_name.lower() == "iOS".lower():
                        self._tap_gesture_iOS(x, y, duration=100, sp_num=sp_num)
                    elif platform_name.lower() == "android".lower():
                        self._tap_gesture_android(x, y, duration=100, sp_num=sp_num)
                    if i < tap_count - 1:
                        time.sleep(delay_between_tap_ms / 1000.0)
                return True

            # Final fallback to TapByScreenCoverageFromSubString
            if not self.TapByScreenCoverageFromSubString(
                name_substring=text_to_find,
                tap_count=tap_count,
                tap_duration_ms=100,
                sp_num=sp_num
            ):
                print(
                    f"Failed to tap element '{element_name}' for Smartphone_{sp_num}: XPath not found, text-based search failed, "
                    "and tap by screen coverage failed"
                )
                return False
            return True

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to tap element '{element_name}' with text search for Smartphone_{sp_num}: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to tap element '{element_name}' for Smartphone_{sp_num} with text search: {wde}")

    def _tap_gesture_iOS(self, x, y, duration, sp_num):
        """Tap at (x, y) on iOS using 'mobile: tap'."""
        self.devices[sp_num]["driver"].execute_script("mobile: tap", {"x": x, "y": y, "duration": duration})

    def _tap_gesture_android(self, x, y, duration, sp_num):
        """Tap at (x, y) on Android using 'mobile: clickGesture'."""
        self.devices[sp_num]["driver"].execute_script(
            "mobile: clickGesture",
            {"x": x, "y": y, "tapCount": 1, "duration": duration}
        )

    def _tap_element_center(self, element, sp_num: int):
        """
        Private method to tap the center of a given element using Appium's mobile: tap command.

        Args:
            element: The WebElement to tap.

        Raises:
            ValueError: If the element's coordinates or dimensions are invalid.
        """
        platform_name = self.devices[sp_num]["capabilities"].get(
            "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
        ).lower()

        try:
            rect = element.rect
            x = rect['x'] + rect['width'] / 2
            y = rect['y'] + rect['height'] / 2
            size = element._parent.get_window_size()
            if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                raise ValueError("Invalid screen dimensions returned by driver")
            if x < 0 or x > size['width'] or y < 0 or y > size['height']:
                raise ValueError(
                    f"Failed to tap element: Coordinates (x={x}, y={y}) are outside "
                    f"screen range (width={size['width']}, height={size['height']})"
                )
            if platform_name.lower() == "iOS".lower():
                self._tap_gesture_iOS(x, y, duration=100, sp_num=sp_num)
            elif platform_name.lower() == "android".lower():
                self._tap_gesture_android(x, y, duration=100, sp_num=sp_num)
        except (ValueError, KeyError) as ve:
            raise ValueError(f"Invalid element coordinates or dimensions: {ve}")

    def TapElementById(self, element_name: str, sp_num: Optional[int] = None) -> bool:
        """
        Taps an element using its ID on the specified smartphone.

        Args:
            element_name (str): The ACCESSIBILITY ID of the element to tap.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the tap is successful.

        Raises:
            ValueError: If element_name is invalid or sp_num is not found.
            NoSuchElementException: If the element is not found.
            WebDriverException: If there is an issue with the WebDriver.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not element_name or not isinstance(element_name, str):
                raise ValueError(f"Invalid element_name: '{element_name}' must be a non-empty string")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
            self.devices[sp_num]["driver"].find_element(AppiumBy.ACCESSIBILITY_ID, element_name).click()
            return True
        except ValueError as ve:
            raise ValueError(f"Failed to tap element by ID '{element_name}' for Smartphone_{sp_num}: {ve}")
        except NoSuchElementException as nse:
            raise NoSuchElementException(f"Failed to tap element by ID '{element_name}' for Smartphone_{sp_num}: {nse}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to tap element by ID '{element_name}' for Smartphone_{sp_num}: {wde}")

    def TapElementByXPath(self, element_name: str, sp_num: Optional[int] = None) -> bool:
        """
        Taps an element using its XPath on the specified smartphone.

        Args:
            element_name (str): The XPath of the element to tap.
            sp_num (Optional[int]): Smartphone identifier.

        Returns:
            bool: True if the tap is successful.

        Raises:
            ValueError: If element_name is invalid or sp_num is not found.
            NoSuchElementException: If the element is not found.
            StaleElementReferenceException: If the element reference becomes stale.
            WebDriverException: If there is an issue with the WebDriver.
        """
        try:
            if sp_num is None or not isinstance(sp_num, int) or sp_num < 0:
                raise ValueError(f"Invalid sp_num: {sp_num} must be a non-negative integer")
            if sp_num not in self.devices:
                raise ValueError(f"Device {sp_num} not found in loaded configurations")
            if not element_name or not isinstance(element_name, str):
                raise ValueError(f"Invalid element_name: '{element_name}' must be a non-empty string")
            if self.devices[sp_num]["driver"] is None:
                raise ValueError(f"InitSmartphone must be called first for device {sp_num}")
            webdriver_elem = self.devices[sp_num]["driver"].find_element(AppiumBy.XPATH, element_name)
            self._tap_element_center(webdriver_elem, sp_num=sp_num)
            return True
        except ValueError as ve:
            raise ValueError(f"Failed to tap element by XPath '{element_name}' for Smartphone_{sp_num}: {ve}")
        except NoSuchElementException as nse:
            raise NoSuchElementException(f"Failed to tap element by XPath '{element_name}' for Smartphone_{sp_num}: {nse}")
        except StaleElementReferenceException as sre:
            raise StaleElementReferenceException(f"Failed to tap element by XPath '{element_name}' for Smartphone_{sp_num}: {sre}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to tap element by XPath '{element_name}' for Smartphone_{sp_num}: {wde}")

    def TapElementByScreenCoverage(self, x_percentage: float, y_percentage: float, tap_count: int, tap_duration_ms: int, sp_num: Optional[int] = None) -> bool:
        """
        Taps at screen coordinates derived from percentage values using Appium's mobile: tap command.

        Args:
            x_percentage (float): X-coordinate as a percentage of screen width (0.0 to 1.0).
            y_percentage (float): Y-coordinate as a percentage of screen height (0.0 to 1.0).
            tap_count (int): Number of times to tap the coordinates.
            tap_duration_ms (int): Duration of each tap in milliseconds.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the tap(s) were successful.

        Raises:
            ValueError: If input parameters are invalid (e.g., percentages out of range, negative tap count or duration, or invalid sp_num).
            WebDriverException: If there's an issue with the WebDriver interaction.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]

            # Validate inputs
            if not isinstance(x_percentage, (int, float)) or x_percentage < 0.0 or x_percentage > 1.0:
                raise ValueError(f"Invalid x_percentage: {x_percentage} must be a number between 0.0 and 1.0")
            if not isinstance(y_percentage, (int, float)) or y_percentage < 0.0 or y_percentage > 1.0:
                raise ValueError(f"Invalid y_percentage: {y_percentage} must be a number between 0.0 and 1.0")
            if not isinstance(tap_count, int) or tap_count < 0:
                raise ValueError(f"Invalid tap_count: {tap_count} must be a non-negative integer")
            if not isinstance(tap_duration_ms, int) or tap_duration_ms < 0:
                raise ValueError(f"Invalid tap_duration_ms: {tap_duration_ms} must be a non-negative integer")

            platform_name = self.devices[sp_num]["capabilities"].get(
                "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
            ).lower()

            # Get screen dimensions
            window_size = driver.get_window_size()
            if not isinstance(window_size, dict) or 'width' not in window_size or 'height' not in window_size:
                raise ValueError("Invalid screen dimensions returned by driver")
            screen_width = window_size['width']
            screen_height = window_size['height']

            # Calculate absolute coordinates
            x = x_percentage * screen_width
            y = y_percentage * screen_height

            # Validate coordinates
            if x < 0 or x > screen_width or y < 0 or y > screen_height:
                raise ValueError(
                    f"Calculated coordinates (x={x}, y={y}) are outside "
                    f"screen range (width={screen_width}, height={screen_height})"
                )

            # Perform taps
            for i in range(tap_count):
                if platform_name.lower() == "iOS".lower():
                        self._tap_gesture_iOS(x, y, duration=100, sp_num=sp_num)
                elif platform_name.lower() == "android".lower():
                    self._tap_gesture_android(x, y, duration=100, sp_num=sp_num)
                if i < tap_count - 1:
                    time.sleep(tap_duration_ms / 1000.0)  # Apply delay between taps

            return True

        except WebDriverException as wde:
            raise WebDriverException(
                f"Failed to tap at screen coverage (x={x_percentage}, y={y_percentage}) on device {sp_num} with "
                f"tap_count={tap_count}, duration={tap_duration_ms}ms: {wde}"
            )

    def GetElementText(self, element_name: str, sp_num: Optional[int] = None) -> str:
        """
        Retrieves the text of an element using a resolved XPath or text-based fallback.

        Args:
            element_name (str): The logical name of the element or an XPath expression.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            str: The text of the element.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the element's text is not found or empty.
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element_name or not isinstance(element_name, str):
                raise ValueError(f"Invalid element_name: '{element_name}' must be a non-empty string")

            xpath = None
            xml_source = driver.page_source
            elem = None
            text_to_find = element_name

            # Check if the element_name is an XPath (starts with /)
            if element_name.startswith("/"):
                xpath = element_name
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element_name)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                xpath = self._resolve_xpath(element_name)

            if xpath is not None:
                # Use the provided or resolved XPath to get the element
                elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # Fallback to finding the deepest matching element by text
            if elem is None:
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                if match is not None:
                    elem = match["element"]
                    # Construct XPath from the found element
                    xpath = self._element_to_xpath(elem)
                    if xpath is None:
                        raise ValueError(f"Could not construct XPath for element '{element_name}'")
                    # Re-fetch element with constructed XPath for consistency
                    elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # If no element is found, raise an exception
            if elem is None:
                raise ValueError(f"No element found for '{element_name}' in XML source on device {sp_num}")

            # Extract text from element (try text, then value attribute)
            text = elem.text if elem.text else elem.attrib.get("value", "")
            if not text:
                print(f"Text not found or empty for element '{element_name}' on device {sp_num}")
                return None
            return text

        except WebDriverException as wde:
            raise WebDriverException(f"WebDriver error while getting text for '{element_name}' on device {sp_num}: {wde}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"XML parsing failed while getting text for '{element_name}' on device {sp_num}: {le}")

    def GetElementTextById(self, element_name: str, sp_num: Optional[int] = None) -> str:
        """
        Retrieves the text of an element using its ID.

        Args:
            element_name (str): The ACCESSIBILITY ID of the element.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            str: The text of the element.

        Raises:
            ValueError: If element_name is invalid or sp_num is invalid.
            AssertionError: If the element's text is not found or empty.
            NoSuchElementException: If the element is not found.
            WebDriverException: If there is an issue with the WebDriver.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]

            if not element_name or not isinstance(element_name, str):
                raise ValueError(f"Invalid element_name: '{element_name}' must be a non-empty string")
            element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, element_name)
            text = element.text or ""
            if not text:
                print(f"Text not found or empty for element with ID '{element_name}' on device {sp_num}")
                return None
            return text

        except WebDriverException as wde:
            raise WebDriverException(f"Failed to get text by ID for '{element_name}' on device {sp_num}: {wde}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"XML parsing failed while getting text for '{element_name}' on device {sp_num}: {le}")

    def GetElementTextByXPath(self, element_name: str, sp_num: Optional[int] = None) -> str:
        """
        Retrieves the text of an element using a resolved XPath.

        Args:
            element_name (str): The logical name of the element or an XPath expression.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            str: The text of the element.

        Raises:
            ValueError: If element_name is invalid, XPath is not found, or sp_num is invalid.
            AssertionError: If the element's text is not found or empty.
            NoSuchElementException: If the element is not found.
            WebDriverException: If there is an issue with the WebDriver.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element_name or not isinstance(element_name, str):
                raise ValueError(f"Invalid element_name: '{element_name}' must be a non-empty string")

            xpath = None
            # Check if the element_name is an XPath (starts with /)
            if element_name.startswith("/"):
                xpath = element_name
            else:
                # Try resolving the element as a logical name

                xpath = self._resolve_xpath(element_name)
                if xpath is None:
                    raise ValueError(f"No XPath found for element '{element_name}' in mapping file for device {sp_num}")

            element = driver.find_element(AppiumBy.XPATH, xpath)
            text = element.text or ""
            if not text:
                print(f"Text not found or empty for element '{element_name}' with XPath '{xpath}' on device {sp_num}")
                return None
            return text
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to get text by XPath for '{element_name}' on device {sp_num}: {wde}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"XML parsing failed while getting text for '{element_name}' on device {sp_num}: {le}")

    def CheckElementProperty(self, element: str, attribute: str, expected: str, comparison: str, sp_num: Optional[int] = None) -> bool:
        """
        Checks an element's attribute against an expected value using a specified comparison.

        Args:
            element (str): The logical name of the element or an XPath expression.
            attribute (str): The attribute to check.
            expected (str): The expected value.
            comparison (str): The comparison operator (e.g., '==', 'contains', '<=').
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the comparison is successful.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the attribute is not found, empty, or the comparison fails.
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not attribute or not isinstance(attribute, str):
                raise ValueError(f"Invalid attribute: '{attribute}' must be a non-empty string")
            if not isinstance(expected, str):
                raise ValueError(f"Invalid expected: '{expected}' must be a string")
            if not comparison or not isinstance(comparison, str):
                raise ValueError(f"Invalid comparison: '{comparison}' must be a non-empty string")

            xpath = None
            xml_source = driver.page_source
            elem = None
            text_to_find = element

            # Check if the element is an XPath (starts with / or //)
            if element.startswith('/') or element.startswith('//'):
                xpath = element
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            if xpath is not None:
                # Use the provided or resolved XPath to get the element
                elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # Fallback to finding the deepest matching element by text
            if elem is None:
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                if match is not None:
                    elem = match["element"]
                    # Construct XPath from the found element
                    xpath = self._element_to_xpath(elem)
                    if xpath is None:
                        raise ValueError(f"Could not construct XPath for element '{element}'")
                    # Re-fetch element with constructed XPath for consistency
                    elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # If no element is found, raise an exception
            if elem is None:
                raise ValueError(f"No element found for '{element}' in XML source on device {sp_num}")

            # Get the attribute value
            actual = elem.attrib.get(attribute, "")
            if not actual:
                raise AssertionError(f"Attribute '{attribute}' not found or empty on element '{element}' on device {sp_num}")

            # Perform comparison
            if comparison == "==":
                if actual != expected:
                    print(f"Element '{element}' attribute '{attribute}'={actual}, expected={expected} for comparison '==' on device {sp_num}")
                    return False
                return True
            if comparison == "!=":
                if actual == expected:
                    print(f"Element '{element}' attribute '{attribute}'={actual}, not expected={expected} for comparison '!=' on device {sp_num}")
                    return False
                return True
            if comparison == "contains":
                if expected not in actual:
                    print(f"Element '{element}' attribute '{attribute}'={actual} does not contain '{expected}' on device {sp_num}")
                    return False
                return True
            if comparison == "!contains":
                if expected in actual:
                    print(f"Element '{element}' attribute '{attribute}'={actual} contains '{expected}', not expected on device {sp_num}")
                    return False
                return True
            if comparison == "startsWith":
                if not actual.startswith(expected):
                    print(f"Element '{element}' attribute '{attribute}'={actual} does not start with '{expected}' on device {sp_num}")
                    return False
                return True
            if comparison == "!startsWith":
                if actual.startswith(expected):
                    print(f"Element '{element}' attribute '{attribute}'={actual} starts with '{expected}', not expected on device {sp_num}")
                    return False
                return True
            if comparison == "endsWith":
                if not actual.endswith(expected):
                    print(f"Element '{element}' attribute '{attribute}'={actual} does not end with '{expected}' on device {sp_num}")
                    return False
                return True
            if comparison == "!endsWith":
                if actual.endswith(expected):
                    print(f"Element '{element}' attribute '{attribute}'={actual} ends with '{expected}', not expected on device {sp_num}")
                    return False
                return True

            try:
                actual_num = float(actual)
                expected_num = float(expected)
                if comparison == "<=":
                    if actual_num > expected_num:
                        print(f"Element '{element}' attribute '{attribute}'={actual_num}, expected <= {expected_num} on device {sp_num}")
                        return False
                    return True
                if comparison == ">=":
                    if actual_num < expected_num:
                        print(f"Element '{element}' attribute '{attribute}'={actual_num}, expected >= {expected_num} on device {sp_num}")
                        return False
                    return True
                if comparison == ">":
                    if actual_num <= expected_num:
                        print(f"Element '{element}' attribute '{attribute}'={actual_num}, expected > {expected_num} on device {sp_num}")
                        return False
                    return True
                if comparison == "<":
                    if actual_num >= expected_num:
                        print(f"Element '{element}' attribute '{attribute}'={actual_num}, expected < {expected_num} on device {sp_num}")
                        return False
                    return True
            except ValueError:
                raise ValueError(f"Failed to convert actual='{actual}' or expected='{expected}' to float for numeric comparison '{comparison}' on device {sp_num}")

            raise ValueError(f"Unsupported comparison operator: '{comparison}' on device {sp_num}")

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to check property '{attribute}' for element '{element}' on device {sp_num} due to XML parsing: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to check element property for '{element}' on device {sp_num}: {wde}")
        
    def GetElementProperty(self, element: str, attribute: str, sp_num: Optional[int] = None) -> str:
        """
        Retrieves the value of an element's attribute.

        Args:
            element (str): The logical name of the element or an XPath expression.
            attribute (str): The attribute to retrieve.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            str: The attribute value.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the specified attribute is not found or has no value.
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not attribute or not isinstance(attribute, str):
                raise ValueError(f"Invalid attribute: '{attribute}' must be a non-empty string")

            xpath = None
            xml_source = driver.page_source
            elem = None
            text_to_find = element

            # Check if the element is an XPath (starts with / or //)
            if element.startswith('/') or element.startswith('//'):
                xpath = element
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            if xpath is not None:
                # Use the provided or resolved XPath to get the element
                elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # Fallback to finding the deepest matching element by text
            if elem is None:
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                if match is not None:
                    elem = match["element"]
                    # Construct XPath from the found element
                    xpath = self._element_to_xpath(elem)
                    if xpath is None:
                        raise ValueError(f"Could not construct XPath for element '{element}'")
                    # Re-fetch element with constructed XPath for consistency
                    elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # If no element is found, raise an exception
            if elem is None:
                raise ValueError(f"No element found for '{element}' in XML source on device {sp_num}")

            # Get the attribute value
            value = elem.attrib.get(attribute, "")
            if not value:
                print(f"Attribute '{attribute}' not found or empty on element '{element}' on device {sp_num}")
                return None
            return value

        except WebDriverException as wde:
            raise WebDriverException(f"Failed to get element property for '{element}' on device {sp_num}: {wde}")
        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to get property '{attribute}' for element '{element}' on device {sp_num} due to XML parsing: {le}")

    def GetAllElementMap(self, sp_num: Optional[int] = None) -> str:
        """
        Retrieves the contents of the element mapping file for the specified device.

        Args:
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            str: The contents of the mapping file, or empty string if not found.

        Raises:
            ValueError: If sp_num is invalid.
            FileNotFoundError: If the mapping file is missing.
            IOError: If there is an error reading the mapping file.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            mapping_path = self.devices[sp_num]["mapping_path"]

            if not mapping_path:
                raise ValueError(f"Mapping path is not set for device {sp_num}")
            if not os.path.exists(mapping_path):
                raise FileNotFoundError(f"Mapping file not found at '{mapping_path}' for device {sp_num}")
            with open(mapping_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError as fnf:
            raise FileNotFoundError(f"Failed to read mapping file for device {sp_num}: {fnf}")
        except IOError as ioe:
            raise IOError(f"Failed to read mapping file '{mapping_path}' for device {sp_num}: {ioe}")
        except ValueError as ve:
            raise ValueError(f"Failed to get mapping file for device {sp_num}: {ve}")

    def WaitForElementText(self, element: str, expected_data: str, ignore_case: int, time_ms: int, sp_num: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Waits for an element's text to contain the expected data within a timeout.

        Args:
            element (str): The logical name of the element or an XPath expression.
            expected_data (str): The expected text or substring.
            ignore_case (int): If non-zero, performs case-insensitive matching.
            time_ms (int): Maximum time to wait in milliseconds.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            Tuple[bool, Optional[str]]: (True, element text) if found, (False, None) if not found within timeout.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the text matches but case sensitivity does not align with ignore_case.
            etree.LxmlError: If the XML source is invalid.
            TimeoutError: If the timeout expires without finding the expected text.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not isinstance(expected_data, str):
                raise ValueError(f"Invalid expected_data: '{expected_data}' must be a string")
            if not isinstance(ignore_case, int):
                raise ValueError(f"Invalid ignore_case: {ignore_case} must be an integer")
            if not isinstance(time_ms, (int, float)) or time_ms < 0:
                raise ValueError(f"Invalid time_ms: {time_ms} must be a non-negative integer")

            xpath = None
            text_to_find = element
            end_time = time.time() + time_ms / 1000.0
            poll_interval = 0.5

            # Check if the element is an XPath (starts with / or //)
            if element.startswith('/') or element.startswith('//'):
                xpath = element
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            while time.time() < end_time:
                try:
                    xml_source = driver.page_source
                    elem = None

                    if xpath is not None:
                        # Use the provided or resolved XPath to get the element
                        elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

                    # Fallback to finding the deepest matching element by text
                    if elem is None:
                        match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                        if match is not None:
                            elem = match["element"]
                            # Construct XPath from the found element
                            xpath = self._element_to_xpath(elem)
                            if xpath is None:
                                raise ValueError(f"Could not construct XPath for element '{element}'")
                            # Re-fetch element with constructed XPath for consistency
                            elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

                    if elem is not None:
                        # Extract text from element (try text, then value attribute)
                        text = elem.text if elem.text else elem.attrib.get("value", "")
                        if text:
                            if ignore_case:
                                if expected_data.lower() in text.lower():
                                    return True, text
                                elif expected_data in text:  # Matches but wrong case
                                    raise AssertionError(f"Element '{element}' text='{text}' contains '{expected_data}' but case sensitivity (ignore_case={ignore_case}) does not match on device {sp_num}")
                            else:
                                if expected_data in text:
                                    return True, text
                                elif expected_data.lower() in text.lower():  # Matches but wrong case
                                    print(f"Element '{element}' text='{text}' contains '{expected_data}' but case sensitivity (ignore_case={ignore_case}) does not match on device {sp_num}")
                                    return False, None
                    time.sleep(poll_interval)
                except ValueError as ve:
                    # Continue polling on ValueError (e.g., XPath construction failure)
                    time.sleep(poll_interval)
                    continue

            print(f"Timeout after {time_ms}ms: Expected text '{expected_data}' not found in element '{element}' on device {sp_num}")
            return False, None

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to wait for text in element '{element}' on device {sp_num} due to XML parsing: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to check wait for element text '{element}' on device {sp_num}: {wde}")

    def CheckElementEnabled(self, element: str, displayed: bool, sp_num: Optional[int] = None) -> bool:
        """
        Checks if an element is enabled (accessible) as expected.

        Args:
            element (str): The logical name of the element or an XPath expression.
            displayed (bool): Expected enabled state (True for enabled, False for disabled).
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the element's enabled state matches the expected state.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the element's enabled state does not match the expected state.
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not isinstance(displayed, bool):
                raise ValueError(f"Invalid displayed: {displayed} must be a boolean")

            xpath = None
            xml_source = driver.page_source
            elem = None
            text_to_find = element

            # Check if the element is an XPath (starts with / or //)
            if element.startswith('/') or element.startswith('//'):
                xpath = element
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            if xpath is not None:
                # Use the provided or resolved XPath to get the element
                elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # Fallback to finding the deepest matching element by text
            if elem is None:
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                if match is not None:
                    elem = match["element"]
                    # Construct XPath from the found element
                    xpath = self._element_to_xpath(elem)
                    if xpath is None:
                        raise ValueError(f"Could not construct XPath for element '{element}'")
                    # Re-fetch element with constructed XPath for consistency
                    elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # If no element is found, raise an exception
            if elem is None:
                raise ValueError(f"No element found for '{element}' in XML source on device {sp_num}")

            # Check enabled state
            is_enabled = elem.attrib.get("accessible", "false").lower() == "true"
            if is_enabled != displayed:
                print(f"Element '{element}' enabled={is_enabled}, expected={displayed} on device {sp_num}")
                return False
            return True

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to check enabled state for element '{element}' on device {sp_num} due to XML parsing: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to check element enabled for '{element}' on device {sp_num}: {wde}")

    def WaitForElementPresence(self, element: str, displayed: bool, time_ms: int, sp_num: Optional[int] = None) -> bool:
        """
        Waits for an element to be present and match the expected visibility state within a specified timeout.

        Args:
            element (str): The logical name of the element or an XPath expression.
            displayed (bool): Expected visibility state (True for visible, False for not visible).
            time_ms (int): Timeout in milliseconds to wait for the element.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the element's visibility matches the expected state within the timeout.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the element's visibility does not match the expected state.
            etree.LxmlError: If the XML source is invalid.
            TimeoutError: If the element does not match the expected visibility state within the timeout.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not isinstance(displayed, bool):
                raise ValueError(f"Invalid displayed: {displayed} must be a boolean")
            if not isinstance(time_ms, (int, float)) or time_ms < 0:
                raise ValueError(f"Invalid time_ms: {time_ms} must be a non-negative integer")

            xpath = None
            elem = None
            text_to_find = element
            end_time = time.time() + (time_ms / 1000.0)

            # Check if the element is an XPath (starts with / or //)
            if element.startswith('/') or element.startswith('//'):
                xpath = element
                # Extract name value for fallback
                match = re.search(r"@(name|label|value)=['\"]([^'\"]*?)['\"]", element)
                if match:
                    text_to_find = match.group(2).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            while time.time() < end_time:
                xml_source = driver.page_source

                if xpath is not None:
                    # Normalize XPath quotes and try variations
                    normalized_xpath = re.sub(r"@(\w+)=[']([^']*?)[']", r'@\1="\2"', xpath)
                    xpath_variations = [
                        xpath,
                        normalized_xpath,
                        re.sub(r"@(\w+)=['\"]([^'\"]*?)['\"]", r'@\1[normalize-space(@\1)="\2"]', normalized_xpath)
                    ]
                    for alt_xpath in xpath_variations:
                        try:
                            # Use _get_element_from_xpath for state validation
                            elem = self._get_element_from_xpath(xml=xml_source, xpath=alt_xpath)
                            if elem is not None:
                                # Check visibility
                                actual_visibility = self._is_element_visible(elem, sp_num=sp_num)
                                if actual_visibility == displayed:
                                    return True
                                break  # Exit variations loop if element found but visibility doesn't match
                        except (NoSuchElementException, etree.LxmlError):
                            if not displayed:
                                return True  # Element not found, matches displayed=False
                            continue  # Try next variation

                # Fallback to finding the deepest matching element by text
                if elem is None:
                    match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                    if match is None:
                        try:
                            match = driver.find_element(AppiumBy.XPATH, text_to_find)
                            if match:
                                actual_visibility = match.is_displayed()
                                if actual_visibility == displayed:
                                    return True
                                else:
                                    return False
                        except Exception:
                            # Skip this iteration and try again
                            match = None
                            continue
                    if match is not None:
                        elem = match["element"]
                        # Construct XPath from the found element
                        xpath = self._element_to_xpath(elem)
                        if xpath is None:
                            raise ValueError(f"Could not construct XPath for element '{element}'")
                        # Re-fetch element with constructed XPath for consistency
                        try:
                            elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)
                        except (NoSuchElementException, etree.LxmlError):
                            if not displayed:
                                return True  # Element not found, matches displayed=False
                            elem = None

                    if elem is not None:
                        # Check visibility
                        actual_visibility = self._is_element_visible(elem, sp_num=sp_num)
                        if actual_visibility == displayed:
                            return True

                # If no element found and expecting not displayed, return True
                if elem is None and not displayed:
                    return True

                time.sleep(0.3)

            print(f"Timeout after {time_ms}ms: Element '{element}' visibility={actual_visibility if elem else 'not found'}, expected={displayed} on device {sp_num}")
            return False

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to wait for element '{element}' on device {sp_num} due to XML parsing: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to wait for element presence for '{element}' on device {sp_num}: {wde}")

    def CheckElementPresence(self, element: str, displayed: bool, sp_num: Optional[int] = None) -> bool:
        """
        Checks if an element is present and matches the expected visibility state.

        Args:
            element (str): The logical name of the element or an XPath expression.
            displayed (bool): Expected visibility state (True for visible, False for not visible).
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the element's visibility matches the expected state.

        Raises:
            ValueError: If inputs are invalid, XPath is not found, element cannot be located, or sp_num is invalid.
            AssertionError: If the element's visibility does not match the expected state.
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            self.mapping_path = self.devices[sp_num]["mapping_path"]

            if not element or not isinstance(element, str):
                raise ValueError(f"Invalid element: '{element}' must be a non-empty string")
            if not isinstance(displayed, bool):
                raise ValueError(f"Invalid displayed: {displayed} must be a boolean")

            xpath = None
            xml_source = driver.page_source
            elem = None
            text_to_find = element

            # Check if the element is an XPath (starts with / or //)
            if element.startswith('/') or element.startswith('//'):
                xpath = element
                # Extract name value for fallback if XPath is for XCUIElementTypeOther
                match = re.search(r"@name='([^']*)'", element)
                if match:
                    text_to_find = match.group(1).strip()
            else:
                # Try resolving the element as a logical name
                xpath = self._resolve_xpath(element)

            if xpath is not None:
                # Use the provided or resolved XPath to get the element
                elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # Fallback to finding the deepest matching element by text
            if elem is None:
                match = self._get_deepest_matching_element(xml=xml_source, text_to_find=text_to_find, sp_num=sp_num)
                if match is not None:
                    elem = match["element"]
                    # Construct XPath from the found element
                    xpath = self._element_to_xpath(elem)
                    if xpath is None:
                        raise ValueError(f"Could not construct XPath for element '{element}'")
                    # Re-fetch element with constructed XPath for consistency
                    elem = self._get_element_from_xpath(xml=xml_source, xpath=xpath)

            # If no element is found, raise an exception
            if elem is None:
                raise ValueError(f"No element found for '{element}' in XML source on device {sp_num}")

            # Check visibility
            actual_visibility = self._is_element_visible(elem, sp_num=sp_num)
            if actual_visibility != displayed:
                print(f"Element '{element}' visible={actual_visibility}, expected={displayed} on device {sp_num}")
                return False
            return True

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to check presence of element '{element}' on device {sp_num} due to XML parsing: {le}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to check for element presence for '{element}' on device {sp_num}: {wde}")

    def StopApplication(self, sp_num: Optional[int] = None) -> bool:
        """
        Stops the application by quitting the driver for the specified device.

        Args:
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the application is stopped successfully.

        Raises:
            ValueError: If sp_num is invalid.
            WebDriverException: If quitting the driver fails.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            self.Quit(sp_num)
            return True

        except WebDriverException as wde:
            raise WebDriverException(f"Failed to stop application for device {sp_num}: {wde}")

    def GetCapability(self, capability: str, sp_num: Optional[int] = None) -> Optional[str]:
        """
        Retrieves a specific capability value for the specified device.

        Args:
            capability (str): The capability key to retrieve.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            Optional[str]: The capability value, or None if not found.

        Raises:
            ValueError: If capability is invalid or sp_num is invalid.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            if not capability or not isinstance(capability, str):
                raise ValueError(f"Invalid capability: '{capability}' must be a non-empty string")
            return self.devices[sp_num]["capabilities"].get(
                capability,
                self.devices[sp_num]["capabilities"].get(f"appium:{capability}")
            )
        except ValueError as ve:
            raise ValueError(f"Failed to get capability '{capability}' for device {sp_num}: {ve}")

    def TakeScreenshot(self, path: str, sp_num: Optional[int] = None) -> bool:
        """
        Takes a screenshot and saves it to the specified path for the specified device.

        Args:
            path (str): The file path to save the screenshot.
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Returns:
            bool: True if the screenshot is saved successfully.

        Raises:
            ValueError: If path is invalid or sp_num is invalid.
            WebDriverException: If the screenshot operation fails.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]

            if not path or not isinstance(path, str):
                raise ValueError(f"Invalid path: '{path}' must be a non-empty string")
            return driver.save_screenshot(path)
        except ValueError as ve:
            raise ValueError(f"Failed to take screenshot at '{path}' for device {sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to take screenshot at '{path}' for device {sp_num}: {wde}")

    def Quit(self, sp_num: Optional[int] = None) -> None:
        """
        Quits the Appium driver for the specified device.

        Args:
            sp_num (Optional[int]): Smartphone identifier to select the target device.

        Raises:
            ValueError: If sp_num is invalid.
            WebDriverException: If quitting the driver fails.
        """
        try:
            if sp_num is None or sp_num not in self.devices:
                raise ValueError(f"Invalid sp_num: '{sp_num}' must be a valid device identifier")
            driver = self.devices[sp_num]["driver"]
            if driver:
                driver.quit()
                self.devices[sp_num]["driver"] = None
        except ValueError as ve:
            raise ValueError(f"Failed to quit driver for device {sp_num}: {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to quit driver for device {sp_num}: {wde}")

    def _scroll_to_element_xpath(self, driver, xpath: str, max_swipes: int = 5) -> etree._Element:
        """
        Scrolls to make an element visible using XPath.

        Args:
            driver: The Appium driver instance.
            xpath (str): The XPath of the element.
            max_swipes (int): Maximum number of swipe attempts (default: 5).

        Returns:
            etree._Element: The visible element.

        Raises:
            ValueError: If xpath is invalid.
            WebDriverException: If scrolling or element lookup fails.
            Exception: If the element is not found after max swipes.
        """
        try:
            if not xpath or not isinstance(xpath, str):
                raise ValueError(f"Invalid xpath: '{xpath}' must be a non-empty string")
            for _ in range(max_swipes):
                try:
                    el = driver.find_element(AppiumBy.XPATH, xpath)
                    if el.is_displayed():
                        return el
                except NoSuchElementException:
                    pass
                driver.swipe(200, 600, 200, 100, 500)
            raise Exception(f"Element not found after {max_swipes} swipes with XPath '{xpath}'")
        except ValueError as ve:
            raise ValueError(f"Failed to scroll to element with XPath '{xpath}': {ve}")
        except WebDriverException as wde:
            raise WebDriverException(f"Failed to scroll to element with XPath '{xpath}': {wde}")

    def _extract_coordinates(self, element: ET.Element, screen_width: int, screen_height: int, sp_num: int) -> Tuple[int, int]:
        """
        Extracts x, y coordinates from an XML element's attributes.

        Args:
            element (ET.Element): The XML element to extract coordinates from.
            screen_width (int): Screen width to validate coordinates.
            screen_height (int): Screen height to validate coordinates.

        Returns:
            Tuple[int, int]: The x, y coordinates (center of the element).

        Raises:
            ValueError: If coordinates cannot be extracted or are invalid.
        """
        try:
            platform_name = self.devices[sp_num]["capabilities"].get(
                "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
            ).lower()
            try:
                if platform_name.lower() == "iOS".lower():
                    x, y = self._parse_position_iOS(element)
                elif platform_name.lower() == "android".lower():
                    x, y = self._parse_size_android(element)
            except (TypeError, ValueError):
                x = -1
                y = -1
            if 0 <= x <= screen_width and 0 <= y <= screen_height:
                return x, y
            
            raise ValueError("Unable to extract valid coordinates from element attributes")

        except (ValueError, TypeError) as ve:
            raise ValueError(f"Failed to extract coordinates: {ve}")
        
    def _get_mapping_path(self, sp_num) -> str:
        """
        Retrieves the element mapping file path from the configuration file.

        Returns:
            str: Path to the element mapping file.

        Raises:
            ValueError: If capabilities are not loaded or sp_num is invalid.
            FileNotFoundError: If the configuration file is missing.
            configparser.Error: If the configuration file is invalid.
            KeyError: If the 'elementMapping' key is missing.
        """
        try:
            if not self or not self.config_path:
                raise ValueError("Configuration not loaded. Call LoadPhoneConfiguration first.")
            
            config = configparser.ConfigParser()
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Configuration file not found at '{self.config_path}'")
            config.read(self.config_path, encoding="utf-8")
            section = f"Smartphone_{sp_num}"
            if section not in config:
                raise KeyError(f"Configuration section '{section}' not found in '{self.config_path}'")
            mapping_path = config.get(section, "elementMapping", fallback="")
            if not mapping_path:
                raise KeyError(f"'elementMapping' key not found in section '{section}' of '{self.config_path}'")
            return mapping_path
        except configparser.Error as ce:
            raise configparser.Error(f"Failed to parse configuration file '{self.config_path}': {ce}")
        except FileNotFoundError as fnf:
            raise FileNotFoundError(f"Failed to read configuration file '{self.config_path}': {fnf}")
        except KeyError as ke:
            raise KeyError(f"Failed to get mapping path for Smartphone_{sp_num}: {ke}")
        except ValueError as ve:
            raise ValueError(f"Failed to get mapping path for Smartphone_{sp_num}: {ve}")

    def _resolve_xpath(self, logical_name: str) -> Optional[str]:
        """
        Resolves the XPath for a given logical element name from the mapping file.

        Args:
            logical_name (str): The logical name of the element to look up.

        Returns:
            Optional[str]: The resolved XPath, or None if not found.

        Raises:
            ValueError: If logical_name or mapping_path is invalid.
            FileNotFoundError: If the mapping file is missing.
            IOError: If there is an error reading the mapping file.
            SyntaxError: If a mapping line is malformed.
        """
        try:
            if not logical_name or not isinstance(logical_name, str):
                raise ValueError(f"Invalid logical_name: '{logical_name}' must be a non-empty string")
            if not self.mapping_path:
                raise ValueError("Mapping path is not set; cannot resolve XPath")
            if not os.path.exists(self.mapping_path):
                raise FileNotFoundError(f"Mapping file not found at '{self.mapping_path}'")

            with open(self.mapping_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "<=>" not in line:
                        continue
                    try:
                        key, xpath = map(str.strip, line.split("<=>", 1))
                    except ValueError:
                        raise SyntaxError(f"Malformed mapping line in '{self.mapping_path}': '{line}'")
                    if key == logical_name:
                        if (xpath.startswith('"') and xpath.endswith('"')) or (xpath.startswith("'") and xpath.endswith("'")):
                            xpath = xpath[1:-1]
                        return xpath
            return None

        except FileNotFoundError as fnf:
            raise FileNotFoundError(f"Failed to resolve XPath for '{logical_name}': {fnf}")
        except IOError as ioe:
            raise IOError(f"Failed to read mapping file '{self.mapping_path}' for '{logical_name}': {ioe}")
        except SyntaxError as se:
            raise SyntaxError(f"Failed to parse mapping file '{self.mapping_path}' for '{logical_name}': {se}")
        except Exception as e:
            raise Exception(f"Unexpected error while resolving XPath for '{logical_name}': {e}") from e

    def _extract_element_types(self, xml: str) -> set:
        """
        Extracts all unique element types from the XML page source.

        Args:
            xml (str): The XML page source.

        Returns:
            set: A set of unique element type names (e.g., {'XCUIElementTypeOther', 'XCUIElementTypeButton', ...}).

        Raises:
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            root = etree.fromstring(xml.encode('utf-8'))
            # Extract all unique tag names starting with XCUIElementType
            element_types = set(
                elem.tag for elem in root.xpath('//*') if elem.tag.startswith('XCUIElementType')
            )
            return element_types
        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to parse XML for element types: {le}")

    def _get_element_from_xpath(self, xml: str, xpath: str) -> Optional[etree._Element]:
        """
        Retrieves an element from XML source using the provided XPath.

        Args:
            xml (str): The XML page source.
            xpath (str): The XPath to query.

        Returns:
            Optional[etree._Element]: The first matching element, or None if not found.

        Raises:
            etree.LxmlError: If the XML source is invalid or the XPath is malformed.
        """
        try:
            root = etree.fromstring(xml.encode('utf-8'))
            # Try the original XPath
            elements = root.xpath(xpath)
            if elements:
                return elements[0]

            # Update global ELEMENT_TYPES if empty
            global ELEMENT_TYPES
            if not ELEMENT_TYPES:
                ELEMENT_TYPES = self._extract_element_types(xml)

            # Fallback: Try variations for all element types with name, label, or value attributes
            for attr in ['name', 'label', 'value']:
                match = re.search(fr"@{attr}=['\"]([^'\"]*?)['\"]", xpath)
                if match:
                    attr_value = match.group(1).strip()
                    # Try each element type with single and double quotes, original and normalized
                    for elem_type in ELEMENT_TYPES:
                        single_quote_xpaths = [
                            f"//{elem_type}[@{attr}='{attr_value}']",
                            f"//{elem_type}[normalize-space(@{attr})='{attr_value}']"
                        ]
                        double_quote_xpaths = [
                            f"//{elem_type}[@{attr}=\"{attr_value}\"]",
                            f"//{elem_type}[normalize-space(@{attr})=\"{attr_value}\"]"
                        ]
                        for alt_xpath in single_quote_xpaths + double_quote_xpaths:
                            elements = root.xpath(alt_xpath)
                            if elements:
                                return elements[0]

            return None

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to parse XML or XPath '{xpath}': {le}")

    def _get_deepest_matching_element(self, xml: str, text_to_find: str, sp_num: int) -> Optional[Dict[str, any]]:
        """
        Finds the deepest element in the XML source containing the specified text.

        Args:
            xml (str): The XML page source.
            text_to_find (str): The text to search for in element attributes or text content.

        Returns:
            Optional[Dict[str, any]]: Dictionary with element, x, and y coordinates, or None if not found.

        Raises:
            etree.LxmlError: If the XML source is invalid.
        """
        try:
            root = etree.fromstring(xml.encode('utf-8'))
            matches = []

            # Normalize text_to_find by removing surrounding quotes and normalizing whitespace
            import re
            normalized_text = re.sub(r'^[\'"]|[\'"]$', '', text_to_find).strip()
            # Normalize whitespace: replace multiple spaces with single space
            normalized_text = re.sub(r'\s+', ' ', normalized_text).lower()
            target = normalized_text

            for elem in root.xpath('//*'):
                # Get attributes, removing quotes and normalizing whitespace
                label = re.sub(r'^[\'"]|[\'"]$', '', elem.attrib.get("label", "")).strip()
                label = re.sub(r'\s+', ' ', label).lower()
                name = re.sub(r'^[\'"]|[\'"]$', '', elem.attrib.get("name", "")).strip()
                name = re.sub(r'\s+', ' ', name).lower()
                value = re.sub(r'^[\'"]|[\'"]$', '', elem.attrib.get("value", "")).strip()
                value = re.sub(r'\s+', ' ', value).lower()

                match_score = 0
                if label == target or name == target or value == target:
                    match_score = 3
                elif target in label or target in name or target in value:
                    match_score = 2

                if match_score > 0:
                    platform_name = self.devices[sp_num]["capabilities"].get(
                        "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
                    ).lower()
                    # Check visibility attribute (default to 'true' if missing)
                    if platform_name.lower() == "iOS".lower():
                        visible = self._parse_visibility_iOS(elem)
                    elif platform_name.lower() == "android".lower():
                        visible = self._parse_visibility_android(elem)

                    # Parse width and height, default to 0 if missing or invalid
                    try:
                        if platform_name.lower() == "iOS".lower():
                            width, height = self._parse_size_iOS(elem)
                        elif platform_name.lower() == "android".lower():
                            width, height = self._parse_size_android(elem)
                    except (TypeError, ValueError):
                        width = 0
                        height = 0

                    # Parse x and y coordinates, default to -1 if missing or invalid
                    try:
                        if platform_name.lower() == "iOS".lower():
                            x, y = self._parse_position_iOS(elem)
                        elif platform_name.lower() == "android".lower():
                            x, y = self._parse_size_android(elem)
                    except (TypeError, ValueError):
                        x = -1
                        y = -1

                    # width = int(elem.attrib.get("width", "0"))
                    # height = int(elem.attrib.get("height", "0"))
                    # visible = elem.attrib.get("visible", "true").lower() == "true"
                    # x = int(elem.attrib.get("x", "-1"))
                    # y = int(elem.attrib.get("y", "-1"))
                    depth = len(elem.xpath("ancestor::*"))

                    if width > 0 and height > 0 and visible and x >= 0 and y >= 0:
                        matches.append((match_score, y, depth, width * height, elem, x, y, width, height))

            matches.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
            if matches:
                _, _, _, _, elem, x, y, width, height = matches[0]
                center_x = x + width / 2
                center_y = y + height / 2
                return {"element": elem, "x": center_x, "y": center_y}
            return None

        except etree.LxmlError as le:
            raise etree.LxmlError(f"Failed to parse XML for text '{text_to_find}': {le}")

    def _parse_visibility_iOS(self, elem: etree._Element) -> bool:
        """Return True if the iOS element is visible, based on the 'visible' attribute."""
        return elem.attrib.get("visible", "true").lower() == "true"

    def _parse_visibility_android(self, elem: etree._Element) -> bool:
        """Return True if the Android element is visible, based on the 'displayed' attribute."""
        return elem.attrib.get("displayed", "true").lower() == "true"

    def _parse_size_iOS(self, elem: etree._Element) -> tuple[int, int]:
        """Return (width, height) for an iOS element using 'width' and 'height' attributes."""
        try:
            width = int(elem.attrib.get('width', '0'))
            height = int(elem.attrib.get('height', '0'))
        except (TypeError, ValueError):
            width = 0
            height = 0
        return width, height

    def _parse_size_android(self, elem: etree._Element) -> tuple[int, int]:
        """Return (width, height) for an Android element parsed from the 'bounds' attribute."""
        bounds_str = elem.attrib.get('bounds')
        if not bounds_str:
            return -1, -1

        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if not match:
            return -1, -1

        x1, y1, x2, y2 = map(int, match.groups())
        width = x2 - x1
        height = y2 - y1
        return width, height

    def _parse_position_iOS(self, elem: etree._Element) -> tuple[int, int]:
        """Return (x, y) position of an iOS element using 'x' and 'y' attributes."""
        try:
            x = int(elem.attrib.get('x', '-1'))
            y = int(elem.attrib.get('y', '-1'))
        except (TypeError, ValueError):
            x = -1
            y = -1
        return x, y

    def _parse_position_android(self, elem: etree._Element) -> tuple[int, int]:
        """Return (x, y) center position of an Android element parsed from the 'bounds' attribute."""
        bounds = elem.attrib.get('bounds')
        if not bounds:
            return -1, -1

        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
        if not match:
            return -1, -1

        x1, y1, x2, y2 = map(int, match.groups())
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        return center_x, center_y

    def _is_element_visible(self, elem: etree._Element, sp_num: int) -> bool:
        """
        Checks if an XML element is visible based on its attributes.

        Args:
            elem (etree._Element): The XML element to check.

        Returns:
            bool: True if the element is visible, False otherwise.

        Raises:
            ValueError: If element attributes are invalid or cannot be processed.
        """
        platform_name = self.devices[sp_num]["capabilities"].get(
            "platformName", self.devices[sp_num]["capabilities"].get("appium:platformName", "")
        ).lower()
        try:
            # Check visibility attribute (default to 'true' if missing)
            if platform_name.lower() == "iOS".lower():
                visible_attr = self._parse_visibility_iOS(elem)
            elif platform_name.lower() == "android".lower():
                visible_attr = self._parse_visibility_android(elem)

            # Parse width and height, default to 0 if missing or invalid
            try:
                if platform_name.lower() == "iOS".lower():
                    width, height = self._parse_size_iOS(elem)
                elif platform_name.lower() == "android".lower():
                    width, height = self._parse_size_android(elem)
            except (TypeError, ValueError):
                width = 0
                height = 0

            # Parse x and y coordinates, default to -1 if missing or invalid
            try:
                if platform_name.lower() == "iOS".lower():
                    x, y = self._parse_position_iOS(elem)
                elif platform_name.lower() == "android".lower():
                    x, y = self._parse_size_android(elem)
            except (TypeError, ValueError):
                x = -1
                y = -1

            # Element is visible if it has positive dimensions, valid position, and visible attribute
            return (visible_attr and 
                    width > 0 and 
                    height > 0 and 
                    x >= 0 and 
                    y >= 0)

        except Exception as e:
            raise ValueError(f"Failed to check visibility of element: {str(e)}")

    def _element_to_xpath(self, elem: etree._Element) -> Optional[str]:
        """
        Converts an XML element to a unique XPath expression.

        Args:
            elem (etree._Element): The XML element to convert.

        Returns:
            Optional[str]: The XPath expression for the element, or None if it cannot be constructed.

        Raises:
            ValueError: If the element is invalid or XPath cannot be constructed.
        """
        try:
            if elem is None:
                return None

            # Start with the element's tag
            path_parts = []
            current = elem

            while current is not None:
                tag = current.tag
                if not tag or not isinstance(tag, str):
                    return None

                # Get all siblings with the same tag
                siblings = [sib for sib in current.getparent().xpath(f"./{tag}") if sib.tag == tag] if current.getparent() is not None else [current]
                index = siblings.index(current) + 1 if len(siblings) > 1 else None

                # Build predicates based on attributes (label, name, value)
                predicates = []
                for attr in ['label', 'name', 'value']:
                    value = current.attrib.get(attr)
                    if value and isinstance(value, str):
                        # Escape single quotes by replacing ' with ''
                        escaped_value = value.replace("'", "''")
                        predicates.append(f"@{attr}='{escaped_value}'")

                # Add position predicate if there are multiple siblings
                if index:
                    predicates.append(f"position()={index}")

                # Construct the path part
                if predicates:
                    path_part = f"{tag}[{' and '.join(predicates)}]"
                else:
                    path_part = f"{tag}"

                path_parts.append(path_part)
                current = current.getparent()

            # Reverse and join the path parts
            xpath = '/' + '/'.join(reversed(path_parts))
            return xpath

        except Exception as e:
            raise ValueError(f"Failed to construct XPath for element: {str(e)}")
            
    def _get_capability(self, sp_num: int, capability: str):
        """
        Retrieve a capability value from the specified smartphone's capabilities
        with case-insensitive lookup, handling optional 'appium:' prefix.

        @param sp_num: The smartphone identifier.
        @param capability: The capability name to retrieve.
        @return: The value from capabilities if found; otherwise, None.
        """
        if sp_num not in self.devices:
            raise ValueError(f"Smartphone {sp_num} is not initialized.")

        capabilities = self.devices[sp_num].get("capabilities", {})
        
        keys_to_check = [
            capability,
            f"appium:{capability}",
            capability.lower(),
            f"appium:{capability.lower()}"
        ]

        lowered_keys = {k.lower(): k for k in capabilities}

        for key in keys_to_check:
            lowered_key = key.lower()
            if lowered_key in lowered_keys:
                original_key = lowered_keys[lowered_key]
                return capabilities[original_key]

        return None