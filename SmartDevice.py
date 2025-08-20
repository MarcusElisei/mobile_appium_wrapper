"""
More information for the methods are found in DUST documentation. Feel free to extend. 
"""
from tal import BaseComponent, AddComment, PROJECT_PATH, Time, Prepare, PYTHON_PATH, ComplexParameter
from tal.KeywordDrivenBase.Core.TimeProvider import *
import os
from typing import Union, List
from datetime import datetime

try:
    import easyocr
except ImportError:
    os.system(PYTHON_PATH + ' -m  pip install easyocr')
    import easyocr

try:
    from PIL import Image
except ImportError:
    os.system(PYTHON_PATH + ' -m pip install pytesseract pillow')
    from PIL import Image

try:
    import cv2
except ImportError:
    os.system(PYTHON_PATH + ' -m pip install opencv-python')
    import cv2

try:
    import numpy as np
except ImportError:
    os.system(PYTHON_PATH + ' -m pip install opencv-python numpy')
    import numpy as np

class SmartDeviceConstants():
    CANNOT_ADD_MESSAGE              = "Cannot Send Message"
    CONFIRM_WITH_ASSISTIVE_TOUCH    = "Assistive"
    CONTINUE_ANYWAY                 = "Continue Anyway"
    ACCEPT_BUTTON                   = "Accept"
    iOS_PIN_CAPABILITY              = "iOSUnlockKey"
    iOS_VERSION_CAPABILITY          = "platformVersion"
    DEVICE_NAME_CAPABILITY          = "deviceName"   
    SCREEN_CAPTURE_PATH             = "screenCapturePath"
    OK_BUTTON                       = "OK"
    BACK                            = "Back"
    SETUP_LATER_BUTTON              = "Setup Later"
    CANCEL                          = "Cancel"  
    GENERAL                         = "General"
    EVERYONE                        = "Everyone for"
    RECEIVING_OFF                   = "Receiving Off"
    AIRDROP                         = "Drop"
    SETTINGS_BUTTON                 = "Settings"
    ADDING_KEY_LABEL                = "Adding Key"
    ADD_CAR_KEY                     = "Add Car Key"
    ENTER_PASSCODE                  = "Enter Passcode"
    DONE_BUTTON                     = "Done"
    CONTINUE_BUTTON                 = "Continue"
    NOTES                           = "Notes"

class SmartDeviceUtils():
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)  # Keep OCR loaded

    def find_text_coordinates(self, image_path : str, search_text : str) -> tuple:
        """
        Find the coordinates of a text in a screenshot using EasyOCR.

        @param image_path: Path to the screenshot.
        @param search_text: Text to search for.
        @return: Tuple (Found, x, y):
                 - Found: True if the text is found, False otherwise.
                 - x, y: Coordinates of the text center in image space if found, -1 otherwise.
        """
        try:
            # Read text from the image
            results = self.reader.readtext(image_path, detail=1, contrast_ths=0.05, adjust_contrast=True, add_margin=0.2)

            for (bbox, text, confidence) in results:
                # Flag to determine if the text matches
                tempResult = False

                # Case for single character/digit
                if len(search_text) == 1:
                    tempResult = search_text.lower() == text.lower()
                # Case for longer strings
                else:
                    tempResult = search_text.lower() in text.lower()

                # If a match is found
                if tempResult:
                    # Get the bounding box coordinates
                    top_left = bbox[0]
                    bottom_right = bbox[2]

                    # Calculate the center of the text
                    x_center = int(sum([point[0] for point in bbox]) / 4)
                    y_center = int(sum([point[1] for point in bbox]) / 4)

                    print(f"Text '{search_text}' found at coordinates: x={x_center}, y={y_center}")
                    return True, x_center, y_center

            # If no match is found
            print(f"Text '{search_text}' not found in the image.")
            return False, -1, -1
        
        except Exception as e:
            print(f"Error during OCR: {e}")
            return False, -1, -1
        
    def calculate_screen_coverage(self, image_width : float, image_height : float, x : float, y : float) -> tuple:
        """
        Calculate screen coverage values from image coordinates.

        @param image_width: Width of the screenshot image.
        @param image_height: Height of the screenshot image.
        @param x: X coordinate of the element in the image.
        @param y: Y coordinate of the element in the image.
        @return: Tuple (Normalized screen coverage values for x and y).

        """
        coverage_x = x / image_width
        coverage_y = y / image_height
        print(f"Converted x and y to {coverage_x}, {coverage_y}")
        return coverage_x, coverage_y

class SmartDevice(BaseComponent):
    def __init__(self, device, sp_num, **kwargs):
        super().__init__(**kwargs)
        self.sp_num                         = sp_num
        self._device                        = device
        self.SmartDeviceUtils               = SmartDeviceUtils()
        self.SmartDeviceConstants           = SmartDeviceConstants()
        self.p_DeviceConfig                 = "Undefined"
        self.p_Applications                 = "Undefined"
        self.p_NumericPasscode              = "Undefined"
        self.p_ButtonPasscode               = "Undefined"
        self.p_UIElements                   = "Undefined"
        self.p_AppleIDs                     = "Undefined"
        self.p_AssistiveTouch               = "Undefined"
        self.p_PayAssistiveTouch            = "Undefined"
        self.p_ConfirmWithAssistiveTouch    = "Undefined"
        self.p_HomeScreen                   = "Undefined"
        self.p_Indicators                   = "Undefined"
        self.p_KeypadDigits                 = "Undefined"
        self.p_WalletElements               = "Undefined"
        self.p_CarModelButtons              = "Undefined"
        self.p_MessagingElements            = "Undefined"
        self.p_SystemPopups                 = "Undefined"
        self.p_CarModelKeyLabel             = "Undefined"
        self.p_OPurlLink                    = "Undefined"

    def _loadConfiguration(self, configuration_path: str) -> bool: 
        """
        Loads all settings and capabilities of the intended Logic Analyzer.

        This method should be called first during test execution to configure the Logic Analyzer
        based on the specified configuration file.

        @param configuration_path: The file path of the configuration (.cfg).
                                File should be located in:
                                Workspace/{name_of_project}/Config/Devices/Smartphone/{name_of_file}
        @return: 'True' if the configuration loads successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.LoadPhoneConfiguration(configuration_path)
        except Exception as e:        
            AddComment("Error - SmartDevice._loadConfiguration(): "+str(e))
            return False
        else:
            return True

    def _convertPinToKeyDigits(self, pin : list) -> list: 
        """
            Retrieve the PIN from the smartphone's capabilities and map it to digit identifiers.
            @param pin: A list of characters representing the PIN digits.
            @return: A list of mapped button identifiers corresponding to the PIN digits.
        """
        mappedPin = []

        # Mapping of digits to button identifiers
        mapping_table = {
            "0": self.p_NumericPasscode.digit0,
            "1": self.p_NumericPasscode.digit1,
            "2": self.p_NumericPasscode.digit2,
            "3": self.p_NumericPasscode.digit3,
            "4": self.p_NumericPasscode.digit4,
            "5": self.p_NumericPasscode.digit5,
            "6": self.p_NumericPasscode.digit6,
            "7": self.p_NumericPasscode.digit7,
            "8": self.p_NumericPasscode.digit8,
            "9": self.p_NumericPasscode.digit9,
        }
        
        # Map the PIN digits to button identifiers
        for digit in pin: 
            mappedPin.append(mapping_table[digit])

        return mappedPin

    def _fetchMappedPin(self, mappedValues=False):
        """
	    Retrieve the PIN from the smartphone's capabilities and optionally map it to digit identifiers.
	    This is used for unlocking the phone.

	    @param mappedValues: If True, the method maps each digit in the PIN to its corresponding button identifier.
	    @return: A list of characters representing the PIN if `mappedValues` is False,
	             or a list of mapped button identifiers if `mappedValues` is True.
	             Returns None if the capability is not set.

        """
        # Mapping of digits to button identifiers
        mapping_table = {
            "0": self.p_NumericPasscode.digit0,
            "1": self.p_NumericPasscode.digit1,
            "2": self.p_NumericPasscode.digit2,
            "3": self.p_NumericPasscode.digit3,
            "4": self.p_NumericPasscode.digit4,
            "5": self.p_NumericPasscode.digit5,
            "6": self.p_NumericPasscode.digit6,
            "7": self.p_NumericPasscode.digit7,
            "8": self.p_NumericPasscode.digit8,
            "9": self.p_NumericPasscode.digit9,
        }
            
        # Retrieve the PIN capability
        pin = self.GetCapability(self.SmartDeviceConstants.iOS_PIN_CAPABILITY)
        if pin is not None:
            pin = [str(char) for char in pin]

        # Map the PIN digits to button identifiers if requested
        if mappedValues and pin is not None:
            pin = [mapping_table[char] for char in pin]

        return pin

    def _fetchMappedPasscode(self, mappedValues=False):
        """
	    Retrieve the PIN from the smartphone's capabilities and optionally map it to button identifiers.
	    This is used for unlocking access to the wallet.

	    @param mappedValues: If True, the method maps each digit in the PIN to its corresponding button identifier.
	    @return: A list of characters representing the PIN if `mappedValues` is False,
	             or a list of mapped button identifiers if `mappedValues` is True.
	             Returns None if the capability is not set.

        """
        # Mapping of digits to button identifiers
        mapping_table = {
            "0": self.p_ButtonPasscode.button0,
            "1": self.p_ButtonPasscode.button1,
            "2": self.p_ButtonPasscode.button2,
            "3": self.p_ButtonPasscode.button3,
            "4": self.p_ButtonPasscode.button4,
            "5": self.p_ButtonPasscode.button5,
            "6": self.p_ButtonPasscode.button6,
            "7": self.p_ButtonPasscode.button7,
            "8": self.p_ButtonPasscode.button8,
            "9": self.p_ButtonPasscode.button9,
        }

        # Retrieve the PIN capability
        pin = self.GetCapability(self.SmartDeviceConstants.iOS_PIN_CAPABILITY)
        if pin is not None:
            pin = [str(char) for char in pin]

        # Map the PIN digits to button identifiers if requested
        if mappedValues and pin is not None:
            pin = [mapping_table[char] for char in pin]

        return pin

    def _initSmartPhone(self, alternate_server: str = "", alternate_url: str = "") -> bool: 
        """
        Initializes the smartphone based on the loaded configuration file.

        @param alternate_server: Optional parameter to override the serverURL hostname in the configuration.
        @param alternate_url: Optional parameter to override the serverURL in the configuration.
        @return: 'True' if the initialization is successful without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.InitSmartphone(alternate_server, alternate_url, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice._initSmartPhone(): "+str(e))
            return False
        else:
            return True
        
        
    def _callMacro(self, target_window: str) -> bool:
        """
        Defines project-specific functionality by navigating to a specified window.

        Example: UnlockFourPin(pin)

        @param target_window: The name of the target window.
        @return: 'True' if the operation is successful without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.GoToWindow(target_window, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice._callMacro(): "+str(e))
            return False
        else:
            return True
    
    def Initialization(self) -> bool:
        """
        Loads all capabilities and settings, and initializes the smartphone.

        This method combines the loading of configuration and initialization of the smartphone
        for execution readiness.

        @return: 'True' if the operation is successful without exceptions.
                'False' if an exception occurs during the operation.
        """
        result = True
        configuration_path = f"{str(PROJECT_PATH)}\\Config\\Devices\\Smartphone\\SmartphoneConfig.cfg"
        try:
            result &= self._loadConfiguration(configuration_path)
            result &= self._initSmartPhone()
            self.deviceName = self.GetCapability(capability="deviceName")
            self.phoneId = self.GetCapability(capability="udid")
            self.platformName = self.GetCapability(capability="platformName")
            self.platformVersion = self.GetCapability(capability="platformVersion")
            self.url = self.GetCapability(capability="serverURL")
        except Exception as e:        
            AddComment("Error - SmartDevice.Initialization(): "+str(e))
            return False
        else:
            return result
    
    def SwipeLeft(self, repeat_count: int, back_interval_ms: float) -> bool:
        """
        Performs a swipe-left gesture on the smartphone.

        @param repeat_count: The number of times the swipe gesture is repeated.
        @param back_interval_ms: The interval (in milliseconds) between swipes.
        @return: 'True' if the gesture is performed successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.SwipeLeft(repeat_count, back_interval_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.SwipeLeft(): "+str(e))
            return False
        else:
            return True
        
    
    def SwipeRight(self, repeat_count: int, back_interval_ms: float) -> bool:
        """
        Performs a swipe-right gesture on the smartphone.

        @param repeat_count: The number of times the swipe gesture is repeated.
        @param back_interval_ms: The interval (in milliseconds) between swipes.
        @return: 'True' if the gesture is performed successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.SwipeRight(repeat_count, back_interval_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.SwipeRight(): "+str(e))
            return False
        else:
            return True

      
    def SwipeUp(self, repeat_count: int, back_interval_ms: float) -> bool:
        """
        Performs a swipe-up gesture on the smartphone.

        @param repeat_count: The number of times the swipe gesture is repeated.
        @param back_interval_ms: The interval (in milliseconds) between swipes.
        @return: 'True' if the gesture is performed successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.SwipeUp(repeat_count, back_interval_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.SwipeUp(): "+str(e))
            return False
        else:
            return True
        
        
    def SwipeDown(self, repeat_count: int, back_interval_ms: float) -> bool:
        """
        Performs a swipe-down gesture on the smartphone.

        @param repeat_count: The number of times the swipe gesture is repeated.
        @param back_interval_ms: The interval (in milliseconds) between swipes.
        @return: 'True' if the gesture is performed successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.SwipeDown(repeat_count, back_interval_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.SwipeDown(): "+str(e))
            return False
        else:
            return True
        
    def SetElementText(self, element: str, text: str, append: bool) -> bool:
        '''
        Set the text of the specified UI element.

        This method sets the text of a UI element on the screen. It either replaces the current text with the new text or 
        appends the new text to the existing content, depending on the value of the `append` parameter. The method interacts 
        with the underlying device to perform this action, using a specific device instance identified by `self.sp_num`.

        @param element: The identifier or name of the UI element whose text needs to be set.
        @param text: The text to be entered into the specified element.
        @param append: Boolean flag indicating whether to append the text (True) or replace the existing text (False).
        @return: Returns 'True' if the text is successfully set; returns 'False' if the operation fails or an exception occurs.
        '''
        try:
            self._device.SetElementText(element, text, append, self.sp_num)
        except Exception as e:
            AddComment("Error - SmartDevice.SetElementText(): "+str(e))
            return False
        else:
            return True

    def GoBack(self, repeat_count: int, back_interval_ms: float) -> bool:
        '''
        Perform GoBack gesture on the smartphone.
        @param repeat_count: Number of times Go Back is performed.
        @param back_interval_ms: Interval between Go Back execution in ms.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''  
        try:
            self._device.GoBack(repeat_count, back_interval_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GoBack(): "+str(e))
            return False
        else:
            return True

    
    def EnableBLE(self) -> bool:
        """
        Enables the smartphone's Bluetooth Low Energy (BLE) from the Control Center.

        @return: 'True' if BLE is enabled successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.EnableBLE(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.EnableBLE(): "+str(e))
            return False
        else:
            return True
    
    def DisableBLE(self) -> bool:
        """
        Disables the smartphone's Bluetooth Low Energy (BLE) from the Control Center.

        @return: 'True' if BLE is disabled successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.DisableBLE(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.DisableBLE(): "+str(e))
            return False
        else:
            return True
    
    def ShowNotificationControlPanel(self) -> bool:
        """
        Displays the smartphone's notification or control panel through simulated gestures.

        @return: 'True' if the panel is displayed successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.ShowNotificationControlPanel(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.ShowNotificationControlPanel(): "+str(e))
            return False
        else:
            return True
    
    def HideNotificationControlPanel(self) -> bool:
        """
        Hides the smartphone's notification or control panel through simulated gestures.

        @return: 'True' if the panel is hidden successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.HideNotificationControlPanel(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.HideNotificationControlPanel(): "+str(e))
            return False
        else:
            return True
    
    def UnlockPhone(self) -> bool:
        """
        Unlocks the smartphone up to the passcode screen (if enabled).

        Note: This method does not enter the passcode.

        @return: 'True' if the phone is unlocked successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
            self._device.UnlockDevice(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.UnlockPhone(): "+str(e))
            return False
        else:
            return True
        
    def LockDevice(self) -> bool:
        """
        Locks the smartphone.

        @return: 'True' if the phone is locked successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        try:
             self._device.LockDevice(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.LockDevice(): "+str(e))
            return False
        else:
            return True
        
    def TapElement(self, name: str) -> bool:
        """
        Performs a tap gesture on the specified element.

        @param name: The identifier for the target element (e.g., mapped name, Appium ID, or xPath).
        @return: 'True' if the gesture is performed successfully without exceptions.
                'False' if an exception occurs during the operation.
        """
        result = True
        try:
            inner_result = self._device.TapElement(name, self.sp_num)
            if isinstance(inner_result, bool):
                result &= inner_result
        except Exception as e:        
            AddComment("Error - SmartDevice.TapElement(): "+str(e))
            return False
        else:
            return result
        
    def TapElementExt(self, element_name: str, tap_count: int, delay_between_tap_ms: int) -> bool:
        '''
        Perform Tap gesture to a selected element on the smartphone.
        @param element_name: Name of Mapped Element or Appium element ID, or Appium xPath.
        @param tap_count: Number of times to perform Tap gesture.
        @param delay_between_tap_ms: Wait Duration performed after performing Tap gesture.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''
        result = True
        try:
            inner_result = self._device.TapElementExt(element_name, tap_count, delay_between_tap_ms,  self.sp_num)
            if isinstance(inner_result, bool):
                result &= inner_result
        except Exception as e:        
            AddComment("Error - SmartDevice.TapElementText(): "+str(e))
            return False
        else:
            return result
        
    def TapElementByScreenCoverage(self, x_percentage: float, y_percentage: float, tap_count: int, tap_duration_ms: int, sp_num: int = None) -> bool:
        '''
        Perform Tap gesture by screen coverage to an element on the smartphone.
        @param x_percentage: X coordinate as percentage.
        @param y_percentage: Y coordinate as percentage.
        @param tap_count: Number of times to perform Tap gesture.
        @param tap_duration_ms: Tap Duration.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''
        if not sp_num:
            sp_num = self.sp_num
        try:
            self._device.TapElementByScreenCoverage(x_percentage, y_percentage, tap_count, tap_duration_ms, sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.TapElementByScreenCoverage(): "+str(e))
            return False
        else:
            return True

    def TapByScreenCoverageFromSubString(self, name_substring: str, tap_count: int, tap_duration_ms: int = 100, sp_num: int = None, scroll_distance: int = 50, timeout: int = 8000, scroll_if_needed: bool = False) -> bool:
        """
        Perform a tap gesture on a smartphone screen by searching for an element whose text, label, or value contains a given substring.

        @param name_substring: Substring to search for in the element's name, label, or value.
        @param tap_count: Number of tap gestures to perform.
        @param tap_duration_ms: Duration of each tap in milliseconds. Default is 100 ms.
        @param sp_num: Smartphone number or identifier. If None, uses self.sp_num.
        @param scroll_distance: Distance to scroll (in pixels) when trying to bring an element into view. Default is 50.
        @param timeout: Maximum wait time to find the element in milliseconds. Default is 8000 ms.
        @param scroll_if_needed: If True, scrolls down until the element is found or the end of scrollable content is reached. Default is False.

        @return: True if the tap gesture was performed successfully; False if an exception occurred.
        """
        result = True
        if not sp_num:
            sp_num = self.sp_num
        try:
            inner_result = self._device.TapByScreenCoverageFromSubString(name_substring, tap_count, tap_duration_ms, scroll_distance, timeout, scroll_if_needed, sp_num=self.sp_num)
            if isinstance(inner_result, bool):
                result &= inner_result
        except Exception as e:        
            AddComment("Error - SmartDevice.TapByScreenCoverageFromSubString(): "+str(e))
            return False
        else:
            return result

    def CheckTextPresence(self, name_substring: str, sp_num: int = None, scroll_distance: int = 50, timeout: int = 8000) -> bool:
        '''
        Check if a UI element containing the specified substring in its name, label, or value is present on the smartphone screen.

        @param name_substring: Substring to search for in the element's name, label, or value.
        @param sp_num: Optional smartphone number or identifier if multiple devices are in use.

        @return: True if the element is present and no exception occurred; False if an error occurred or the element is not found.
        '''
        result = True
        try:
            result &= self._device.CheckTextPresence(name_substring, self.sp_num, scroll_distance, timeout)
        except Exception as e:        
            AddComment("Error - SmartDevice.CheckTextPresence(): "+str(e))
            return False
        else:
            return result

    def TapElementByXPath(self, element_name: str) -> bool:
        '''
        Perform Tap gesture to a selected element on the smartphone by passing the raw xpath of the element
        @param element_name: xPath definition of the target element.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''
        try:
            self._device.TapElementByXPath(element_name, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.TapElementByXPath(): "+str(e))
            return False
        else:
            return True
    
    def TapElementById(self, element_name: str) -> bool:
        '''
        Perform Tap gesture to a selected element on the smartphone by passing the raw element id
        @param element_name: ACCESSIBILITY Id of the target element.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''
        try:
            self._device.TapElementById(element_name,  self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.TapElementById(): "+str(e))
            return False
        else:
            return True
        
    def GetElementText(self, element_name: str) -> str: 
        '''
        Use this command to get the current value of selected element.
        @param element_name: Name of Mapped Element.
        @return: Element text if successful, empty string otherwise.
        '''
        try:
            element_text = self._device.GetElementText(element_name, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GetElementText(): "+str(e))
            return None
        return element_text
    
    def GetElementTextById(self, element_name: str) -> str:
        '''
        Use this command to get the current value of selected element.
        @param element_name: Accessibility Id of the target element.
        @return: Element text if successful, empty string otherwise.
        '''
        try:
            element_text = self._device.GetElementTextById(element_name, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GetElementTextById(): "+str(e))
            return None
        return element_text

    def GetElementTextByXPath(self, element_name: str) -> str:
        '''
        Use this command to get the current value of selected element.
        @param element_name: x_path definition of the target element.
        @return: Element text if successful, empty string otherwise.
        '''
        try:
            element_text = self._device.GetElementTextByXPath(element_name, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GetElementTextByXPath(): "+str(e))
            return None
        return element_text
        
    def CheckElementProperty(self, element: str, attribute: str, expected: str, comparison: str) -> bool: 
        '''
        Check the target element attributes.
        @param element: Name of Element.
        @param attribute: Element attribute to check.
        @param expected: Expected value of the attribute selected.
        @param comparison: string: ==, != , contains, !contains, startsWith, !startsWith, endsWith, !endsWith. 
                           numeric: ==, != , <= , >= , > , < }.
        @return 'True' if comparison succeeded
        @return 'False' if comparison failed or exception occurs within the mobile wrapper             
        '''
        result = True
        try:
            result &= self._device.CheckElementProperty(element, attribute, expected, comparison, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.CheckElementProperty(): "+str(e))
            return False
        else:
            return result
        
    def GetElementProperty(self, element: str, attribute: str) -> str: 
        '''
        Get the target element attributes.
        @param element: Name of Element.
        @param attribute: Element attribute to check.
        @return: Element property if successful, empty string otherwise.
        '''
        try:
            element_property = self._device.GetElementProperty(element, attribute, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GetElementProperty(): "+str(e))
            return None
        return element_property 
        
    def GetAllElementMap(self) -> str:
        '''
        Use this command to get a list of all available mapped elements tied to a smartphone.
        @return: Element attribute if successful, empty string otherwise.
        '''
        try:
            element_attribute = self._device.GetAllElementMap(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GetAllElementMap(): "+str(e))
            return None
        return element_attribute 
        
    def WaitForElementText(self, element: str, expected_data: str, ignore_case: int, time_ms: int):
        '''
        Use this command to wait check if the target element contains specified string.
        @param element: Name of Element.
        @param expected_data: Value to check on target element.
        @param ignore_case: Ignores case sensitivity during comparison.
        @param time_ms: Duration on how long the function should wait.
        @return result to determine if expectedData was found.
        @return Element text which is the actual value of target element in string.
        '''
        result = False
        try:
            result, element_text = self._device.WaitForElementText(element, expected_data, ignore_case, time_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.WaiForElementText(): "+str(e))
            return None
        return element_text
    
    def CheckElementEnabled(self, element: str, displayed: bool) -> bool:
        '''
        Check if the target element is enabled or disabled in the current Window.
        @param element: Name of Element.
        @param displayed: True = displayed, False = Not displayed.
        @return 'True' if element enabled
        @return 'False' if element not enabled or exception occurs within the wrapper
        '''
        result = True
        try:
            result &= self._device.CheckElementEnabled(element, displayed, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.CheckElementEnabled(): "+str(e))
            return False
        else:
            return result
    
    def WaitForElementPresence(self, element: str, displayed: bool, time_ms: int) -> bool:
        '''
        Wait until target element will appear or disappeard in the currentWindow.
        @param element: Name of Element.
        @param displayed: True = displayed, False = Not displayed.
        @param time_ms: Duration on how long the function should wait.
        @return 'True' if element appeared/disappeard in the currentWindow.
        @return 'False' if comparison failed or exception occurs within the wrapper
        '''
        result = True
        try:
            result &= self._device.WaitForElementPresence(element, displayed, time_ms, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.WaitForElementPresence(): "+str(e))
            return False
        else:
            return result
        
    def CheckElementPresence(self, element: str, displayed: bool) -> bool:
        '''
        Check if the target element is displayed/not displayed in the current Window.
        @param element: Name of Element.
        @param displayed: True = displayed, False = Not displayed.
        @return 'True' if element displayed/not displayed in the currentWindow.
        @return 'False' if comparison failed or exception occurs within the wrapper
        '''
        result = True
        try:
            result &= self._device.CheckElementPresence(element, displayed, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.CheckElementPresence(): "+str(e))
            return False
        else:
            return result
    
   
    def StartApplication(self, device_name: str, phone_id: str, platform_name: str, platform_version: str, app_package: str, app_activity: str, url: str) -> bool:
        '''
        Start a specific application. Make sure appium server is running.
        @param device_name: Name of the Device.
        @param phone_id: Unique device identifier of the connected physical device.
        @param platform_name: Valid values: Android, iOS.
        @param platform_version: Version of the Operation System.
        @param app_package: Java package/Bundle Id of the app you want to run.
        @param app_activity: Activity name.
        @param url: Link to Appium Server. Make sure Appium Server is running.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''
        try:
            self._device.StartApplication(device_name, phone_id, platform_name, platform_version, app_package, app_activity, url, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.StartApplication(): "+str(e))
            return False
        else:
            return True
        
    def StopApplication(self) -> bool:
        '''
        Stop the running application.
        @return 'True' if exception does not occur within the mobile wrapper
        @return 'False' if exception occurs within the mobile wrapper
        '''
        try:
            self._device.StopApplication(self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.StopApplication(): "+str(e))
            return False
        else:
            return True
        
    def GetCapability(self, capability: str) -> str:
        '''
        Retrieve the specified capability of the device.
    
        This method fetches the value of a specified capability from the connected 
        smartphone. The capability is identified by its name, which is passed as 
        a parameter. If the capability is found, its value is returned.
    
        @param capability: The name of the capability to retrieve. This should be a 
                           valid capability name recognized by the device.
        @return: The value of the capability if retrieval is successful; returns an 
                 empty string if an exception occurs or the capability cannot be retrieved.
        '''
        try:
            capability_value = self._device.GetCapability(capability, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.GetCapability(): "+str(e))
            return None
        else:
            return capability_value

        
    def TakeScreenshot(self, path: str) -> bool:
        '''
        Capture and save a screenshot on the selected smartphone.
        
        This method takes a screenshot of the current screen on the smartphone 
        and saves it to the specified file path.
        
        @param path: The file path (including filename) where the screenshot will be saved. 
                     Ensure the directory exists or is writable.
        @return: 'True' if the screenshot is successfully taken and saved; 
                 returns 'False' if an exception occurs during the operation. 
        '''
        try:
            self._device.TakeScreenshot(path, self.sp_num)
        except Exception as e:        
            AddComment("Error - SmartDevice.TakeScreenshot(): "+str(e))
            return False
        else:
            return True

class SmartDeviceiPhone(SmartDevice):
    def __init__(self, device, sp_num, **kwargs):
        '''
        Initialize a iOS SmartDevice instance.
        @param device: The device object representing the SmartDevice.
        @param sp_num: The SmartDevice number or identifier.
        @param kwargs: Additional keyword arguments.
        '''
        SmartDevice.__init__(self, device, sp_num, **kwargs)

    def LogDeviceScreenShot(self, file_name: str) -> bool:
        '''
        Take and log a screenshot of the device, saving it to the specified file path.
    
        @param file_name: The name of the file where the screenshot will be saved.
        @return: 'True' if the screenshot is successfully taken and saved; 'False' otherwise.
        '''
        result = True
        capability = self.GetCapability(self.SmartDeviceConstants.SCREEN_CAPTURE_PATH)
        if capability is None:
            raise ValueError("Screen capture path is not configured or SmartphoneConfig.cfg was not loaded. Please initialize the device before performing any operations.")
        directory = os.path.dirname(capability)
        new_path = os.path.join(directory, file_name)
        result &= self.TakeScreenshot(new_path)
        return result

    def TapByScreenCoverageFromText(
        self,
        elementToFind: Union[str, List[str]],
        skipIfNotFound: bool = False,
        nb_of_taps: int = 1,
        timeout: int = 2000,
        use_ss_as_backup: bool = False,
        use_only_ss: bool = False,
        scroll_if_needed: bool = False
    ) -> str:
        """
        Attempts to tap visible on-screen text elements either by substring matching or OCR.

        The method first tries to locate and tap each text using TapByScreenCoverageFromSubString.
        If that fails or is disabled via `use_only_ss`, it can fall back to OCR via screenshots.

        Args:
            elementToFind (str | list[str]): One or more strings to search and tap on screen.
            skipIfNotFound (bool): If True, skips missing elements and continues. If False, stops and returns "Failed". Default is False.
            nb_of_taps (int): Number of tap actions to perform per element. Default is 1.
            timeout (int): Max time (in ms) to wait for each element. Default is 2000 ms.
            use_ss_as_backup (bool): If True, fallback to OCR if substring search fails. Default is False.
            use_only_ss (bool): If True, only use OCR; skips substring matching entirely. Overrides use_ss_as_backup. Default is False.
            scroll_if_needed (bool): If True, scrolls during substring search to find off-screen text. Default is False.

        Returns:
            str: 
                - "True" if all required text elements were tapped successfully.
                - "False" if any required element was not tapped (when skipIfNotFound is False).

        Notes:
            - OCR fallback uses SmartDeviceUtils.find_text_coordinates from screenshots.
            - Tap coordinates are calculated using screen coverage, not raw pixels.
            - Reuses coordinates for repeated taps only if the same text was already found.
        """
        if not elementToFind:
            AddComment(f"Error - TapByScreenCoverageFromText: elementToFind '{elementToFind}' must be a non-empty string or list of strings")
            return False
        if not isinstance(nb_of_taps, int) or nb_of_taps < 0:
            AddComment(f"Error - TapByScreenCoverageFromText: Invalid nb_of_taps: {nb_of_taps} must be non-negative")
            return False
        if not isinstance(timeout, int) or timeout < 0:
            AddComment(f"Error - TapByScreenCoverageFromText: Invalid timeout: {timeout} must be non-negative")
            return False
        if not isinstance(skipIfNotFound, bool):
            AddComment(f"Error - TapByScreenCoverageFromText: Invalid skipIfNotFound: {skipIfNotFound} must be a boolean")
            return False

        if not isinstance(elementToFind, list):
            elementToFind = [elementToFind]

        result = True
        screenshot_path = os.path.join(os.getcwd(), "elementSearch.png")
        last_text = None
        last_coords = None
        last_coverage = None

        for inputItem in elementToFind:
            inputItem = str(inputItem)
            if not inputItem:
                AddComment(f"Error - TapByScreenCoverageFromText: Empty string in elementToFind")
                if not skipIfNotFound:
                    return False
                continue

            textFound = False

            # Try TapByScreenCoverageFromSubString if available and allowed
            if hasattr(self._device, 'TapByScreenCoverageFromSubString') and not use_only_ss:
                try:
                    success = self._device.TapByScreenCoverageFromSubString(
                        sp_num=self.sp_num,
                        name_substring=inputItem,
                        tap_count=nb_of_taps,
                        tap_duration_ms=60,
                        timeout=timeout,
                        scroll_if_needed=scroll_if_needed
                    )
                    if success:
                        textFound = True
                except Exception as e:
                    AddComment(f"Failed - TapByScreenCoverageFromSubString for '{inputItem}': {e}")

            # OCR fallback (backup or only mode)
            use_ocr = (use_ss_as_backup and not textFound) or use_only_ss
            if use_ocr:
                for tap_index in range(nb_of_taps):
                    if inputItem == last_text and last_coords and last_coverage:
                        coverageX, coverageY = last_coverage
                        AddComment(f"Reusing previous coordinates for '{inputItem}' (x={coverageX}, y={coverageY}).")
                    else:
                        textFound, xCoord, yCoord = False, None, None
                        start_time = time.time()

                        while (time.time() - start_time) * 1000 < timeout:
                            if not self.TakeScreenshot(screenshot_path):
                                if not skipIfNotFound:
                                    return False
                                break
                            textFound, xCoord, yCoord = self.SmartDeviceUtils.find_text_coordinates(screenshot_path, inputItem)
                            if textFound:
                                break
                            time.sleep(0.1)

                        if not textFound:
                            last_text = None
                            last_coords = None
                            last_coverage = None
                            if not skipIfNotFound:
                                return False
                            break

                        try:
                            with Image.open(screenshot_path) as img:
                                imageWidth, imageHeight = img.size

                            coverageX, coverageY = self.SmartDeviceUtils.calculate_screen_coverage(
                                imageWidth, imageHeight, xCoord, yCoord
                            )

                            last_text = inputItem
                            last_coords = (xCoord, yCoord)
                            last_coverage = (coverageX, coverageY)
                        except Exception as e:
                            AddComment(f"Failed - TapByScreenCoverageFromText: Failed to process screenshot for '{inputItem}': {e}")
                            if not skipIfNotFound:
                                return False
                            break

                    try:
                        success = self.TapElementByScreenCoverage(coverageX, coverageY, 1, 150)
                        result &= success
                        if not success and not skipIfNotFound:
                            return False
                    except Exception as e:
                        AddComment(f"Failed - TapByScreenCoverageFromText: Tap failed for '{inputItem}' at coordinates (x={coverageX}, y={coverageY}): {e}")
                        if not skipIfNotFound:
                            return False

        return True if result else False

    def IsTextOnScreen(self, textToMatch: Union[str, List[str]], timeout: int = 5000, check_interval: int = 100, log_if_not_found: bool = False, use_ss_as_backup: bool = False) -> bool:
        """
        Checks whether one or more given text strings are currently visible on the smartphone screen.

        This method first attempts to detect the text using the device's native `CheckTextPresence` method.
        If not found and `use_ss_as_backup` is enabled, it falls back to OCR-based detection using a screenshot.

        Args:
            textToMatch (Union[str, List[str]]): A single string or list of strings to search for on the screen.
            timeout (int): Maximum time to wait for the text(s) to appear, in milliseconds. Default is 5000 ms.
            check_interval (int): Interval between checks, in milliseconds. Default is 100 ms.
            log_if_not_found (bool): Whether to log detailed messages if the text is not found. Default is False.
            use_ss_as_backup (bool): Whether to use OCR-based screenshot fallback if CheckTextPresence fails. Default is False.

        Returns:
            bool: True if all specified text values are found within the timeout; False otherwise.

        Notes:
            - If `textToMatch` is empty or invalid, the function logs an error and returns False.
            - If `CheckTextPresence` is unavailable or fails, OCR is used if enabled.
            - All texts in the list must be found to return True.
        """
        if not textToMatch:
            AddComment(f"Error - IsTextOnScreen: textToMatch '{textToMatch}' must be a non-empty string or list of strings")
            return False
        if not isinstance(timeout, int) or timeout < 0:
            AddComment(f"Error - IsTextOnScreen: Invalid timeout: {timeout} must be non-negative")
            return False
        if not isinstance(check_interval, int) or check_interval <= 0:
            AddComment(f"Error - IsTextOnScreen: Invalid check_interval: {check_interval} must be positive")
            return False
        if not isinstance(log_if_not_found, bool):
            AddComment(f"Error - IsTextOnScreen: Invalid log_if_not_found: {log_if_not_found} must be a boolean")
            return False

        if not isinstance(textToMatch, list):
            textToMatch = [textToMatch]

        end_time = time.time() * 1000 + timeout  # in ms

        while time.time() * 1000 < end_time:
            texts_found = []

            for text in textToMatch:
                text = str(text)
                if not text:
                    if log_if_not_found:
                        AddComment("Error - IsTextOnScreen: Empty string in textToMatch")
                    texts_found.append(False)
                    continue

                textFound = False

                # Try CheckTextPresence
                if hasattr(self._device, 'CheckTextPresence'):
                    try:
                        if self._device.CheckTextPresence(sp_num=self.sp_num, name_substring=text, timeout=timeout):
                            textFound = True
                        elif log_if_not_found:
                            AddComment(f"CheckTextPresence did not find '{text}'")
                    except Exception as e:
                        if log_if_not_found:
                            AddComment(f"CheckTextPresence failed for '{text}': {e}")

                # Fallback to OCR
                if not textFound and use_ss_as_backup:
                    screenshot_path = os.path.join(os.getcwd(), "elementSearch.png")
                    if self.TakeScreenshot(screenshot_path):
                        textFound, _, _ = self.SmartDeviceUtils.find_text_coordinates(screenshot_path, text)
                        if not textFound and log_if_not_found:
                            AddComment(f"OCR did not find '{text}' in screenshot")
                    else:
                        if log_if_not_found:
                            AddComment(f"Failed to take screenshot for '{text}'")

                texts_found.append(textFound)

            # Final check: were ALL texts found?
            if all(texts_found):
                return True

            time.sleep(check_interval / 1000.0)

        if log_if_not_found:
            AddComment(f"Timeout reached after {timeout}ms: Text(s) '{textToMatch}' not found")
        return False
    
    def UnlockPin(self, key_digit: list = None) -> bool:
        """
        Unlocks the device by tapping the specified PIN digits on the screen.

        If no `key_digit` list is provided, the method will attempt to fetch a pre-mapped PIN
        using internal configuration (e.g., from self._fetchMappedPin(mappedValues=True)).

        Each digit in the list should be a complex parameter corresponding to one of the following:
            - SmartDevice.p_NumericPasscode.digit0
            - SmartDevice.p_NumericPasscode.digit1
            - SmartDevice.p_NumericPasscode.digit2
            - SmartDevice.p_NumericPasscode.digit3
            - SmartDevice.p_NumericPasscode.digit4
            - SmartDevice.p_NumericPasscode.digit5
            - SmartDevice.p_NumericPasscode.digit6
            - SmartDevice.p_NumericPasscode.digit7
            - SmartDevice.p_NumericPasscode.digit8
            - SmartDevice.p_NumericPasscode.digit9

        Args:
            key_digit (list, optional): A list of complex parameters representing the PIN digits to tap.
                                        If not provided, the mapped PIN will be fetched automatically.

        Returns:
            bool: True if all digits were tapped successfully and the device is unlocked;
                False if any step fails.
        """
        result = True
        if not key_digit:
            pin = self._fetchMappedPin(mappedValues=True)
            key_digit = pin

        result &= self.UnlockPhone()
        if not self.WaitForElementPresence(element=key_digit[0], displayed=True, time_ms=1000.00):
            AddComment("The PIN did not appear on the screen.")
            return False
        
        for digit in key_digit:
            result &= self.TapElement(digit)

        return result
    
    def StartApp(self, app : str) -> bool:
        '''
        Start a specific application. Make sure appium server is running.
        :param app: Java package/Bundle Id of the app you want to run.
        '''
        result = True
        result &= self.StartApplication(device_name=self.deviceName, 
                                        phone_id=self.phoneId, 
                                        platform_name=self.platformName, 
                                        platform_version=self.platformVersion, 
                                        app_package=app, 
                                        app_activity=app, 
                                        url=self.url)
        
        if not result:
            AddComment(f"Could not start app {app}.")
            return result
            
        return result
    
    def TurnOffOnBLE(self) -> bool:
        '''
        Toggle Bluetooth off and on using the smartphone's settings.
        
        @return: 'True' if Bluetooth was toggled successfully; 'False' otherwise.
        '''
        result = True
        if not self.StartApp(app=self.p_BundleIds.Settings):
            return False
        self.SwipeDown(repeat_count=2, back_interval_ms=200.00)
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothButton, displayed=True, time_ms=3000.00):
            result &= self.TapElement(name=self.p_UIElements.bluetoothButton)
        else:
            AddComment("Bluetooth button not present on screen. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOffOnBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothSwitch, displayed=True, time_ms=3000.00):
            if self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="1", ignore_case=False, time_ms=6000.00):
                result &= self.TapElement(name=self.p_UIElements.bluetoothSwitch)
                if self.WaitForElementPresence(element=self.p_UIElements.bluetoothSwitch, displayed=True, time_ms=2000.00):
                    result &= self.TapElement(name=self.p_UIElements.bluetoothSwitch)
            elif self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="0", ignore_case=False, time_ms=6000.00):
                result &= self.TapElement(name=self.p_UIElements.bluetoothSwitch)
        else:
            AddComment("Bluetooth switch not present on screen. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOffOnBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False
        if self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="1", ignore_case=True, time_ms=6000.00):
            AddComment("Bluetooth was turned off and on.")
            result &= True
        else:
            AddComment("Turn off on BLE did not perform as expected. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOffOnBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            result &= False
        if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=3000.00):
            self.TapElement(self.p_UIElements.backButton)
        if self.WaitForElementPresence(element=self.p_UIElements.settingsButton, displayed=True, time_ms=2000.00):
            self.TapElement(self.p_UIElements.settingsButton)
        if not self.StartApp(app=self.p_BundleIds.Wallet):
            return False
        return result
        
    def TurnOffBLE(self) -> bool:
        '''
        Turn off Bluetooth on the smartphone.
        '''
        result = True
        if not self.StartApp(app=self.p_BundleIds.Settings):
            return False
        self.SwipeDown(repeat_count=2, back_interval_ms=200.00)
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothButton, displayed=True, time_ms=3000.00):
            result &= self.TapElement(self.p_UIElements.bluetoothButton)
        else:
            AddComment("Bluetooth button not present on screen. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOffBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False 
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothSwitch, displayed=True, time_ms=3000.00):
            if self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="1", ignore_case=True, time_ms=6000.00):
                result &= self.TapElement(self.p_UIElements.bluetoothSwitch)
            if self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="0", ignore_case=True, time_ms=6000.00):
                AddComment("Bluetooth was turned off.")
                result &= True
            else:
                AddComment("Turn Off BLE did not perform as expected. Check log files for screen shot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOffBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
                result &= False
        else:
            AddComment("Bluetooth switch not present on screen. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOffBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False  
        if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=3000.00):
            self.TapElement(self.p_UIElements.backButton)
        if self.WaitForElementPresence(element=self.p_UIElements.settingsButton, displayed=True, time_ms=2000.00):
            self.TapElement(self.p_UIElements.settingsButton)
        if not self.StartApp(app=self.p_BundleIds.Wallet):
            return False
        return result

    def TurnOnBLE(self) -> bool:
        '''
        Turn on Bluetooth on the smartphone.
        '''
        result = True
        if not self.StartApp(app=self.p_BundleIds.Settings):
            return False
        self.SwipeDown(repeat_count=2, back_interval_ms=200.00)
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothButton, displayed=True, time_ms=3000.00):
            result &= self.TapElement(self.p_UIElements.bluetoothButton)
        else:
            AddComment("Bluetooth button not present on screen. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOnBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False 
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothSwitch, displayed=True, time_ms=3000.00):
            if self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="0", ignore_case=False, time_ms=6000.00):
                result &= self.TapElement(self.p_UIElements.bluetoothSwitch)
            if self.WaitForElementText(element=self.p_UIElements.bluetoothSwitch, expected_data="1", ignore_case=True, time_ms=6000.00):
                AddComment("Bluetooth was turned on.")
                result &= True
            else:
                AddComment("Turn On BLE did not perform as expected. Check log files for screen shot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOnBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
                result &= False
        else:
            AddComment("Bluetooth switch not present on screen. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TurnOnBLE_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False  
        if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=3000.00):
            self.TapElement(self.p_UIElements.backButton)
        if self.WaitForElementPresence(element=self.p_UIElements.settingsButton, displayed=True, time_ms=2000.00):
            self.TapElement(self.p_UIElements.settingsButton)
        if not self.StartApp(app=self.p_BundleIds.Wallet):
            return False
        return result
    
    def SetBluetoothState(self, state : int) -> bool:
        """
        Toggles Bluetooth on or off via the device's settings.

        This method navigates to the Bluetooth settings, checks the current state, and toggles it if needed.
        If any step fails, a screenshot is captured, and a comment is logged.

        @param state: Desired Bluetooth state; `0` for off, `1` for on.
        @return: `True` if the state is set successfully; `False` otherwise.
        """
        result = True
        
        if state not in [0,1]:
            raise ValueError("The Bluetooth state must be 0 (off) or 1 (on).")

        if not self.StartApp(app=self.p_BundleIds.Settings):
            return False
        
        self.SwipeDown(repeat_count=2, back_interval_ms=200.00)
        if self.WaitForElementPresence(element=self.p_UIElements.bluetoothButton, displayed=True, time_ms=3000.00):
            result &= self.TapElement(self.p_UIElements.bluetoothButton)
            if self.WaitForElementPresence(element=self.p_UIElements.bluetoothSwitch, displayed=True, time_ms=2000.00) == True: 
                crtBtState = self.GetElementText(element_name=self.p_UIElements.bluetoothSwitch)

                if crtBtState is None:
                    AddComment("Could not retrieve the Bluetooth switch value!")
                    result &= False  
                else:
                    if crtBtState != str(state): 
                        result &= self.TapElement(name=self.p_UIElements.bluetoothSwitch)
                        if result == True: 
                            AddComment(f"Bluetooth turned {'off' if state == '0' else 'on'}")
                        else: 
                            AddComment(f"Could not turn Bluetooth {'off' if state == '0' else 'on'}!")
                            self.LogDeviceScreenShot(f"{Prepare._tcName}_SetBluetoothState_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
                            result &= False
                    else:
                        AddComment(f"Bluetooth was already turned {'off' if state == '0' else 'on'}")
            else:
                AddComment("The Bluetooth switch was not found on the screen !")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_SetBluetoothState_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
                result &= False
        else:
            AddComment("The Bluetooth button (settings) was not found on the screen !")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_SetBluetoothState_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            result &= False
        
        return result

    def GetNFCReadyState(self, dk_label : str = None, dk_xpath : str = None) -> bool:
        '''
        Prepares the NFC system for use by interacting with the smartphone's Wallet app and relevant UI elements.

        This method automates the process of verifying that the NFC system is ready. It navigates through the necessary UI screens,
        taps on relevant elements, handles passcode input if required, and confirms the NFC readiness state. If any step fails,
        a screenshot is captured, and an appropriate comment is logged.

        Parameters:
            dk_label (str, optional): An optional label identifying the Device Key (DK) to be used during NFC preparation.
                                    This helps determine which car key to communicate with based on visible text in the Wallet UI.
                                    If both `dk_label` and `dk_xpath` are provided, the label will be used with priority.
                                    The label must exist as visible text on the screen (not as an XPath).

            dk_xpath (str, optional): An alternative way to locate the DK using its XPath in the Wallet UI.
                                    This will be used only if `dk_label` is not provided or is set to "UNDEFINED" in the data definition.

        Returns:
            bool: True if NFC is successfully prepared and reaches a ready state; False otherwise.
        '''
        result = True

        pin = self._fetchMappedPasscode(mappedValues=False)
        if pin is None:
            AddComment("Pin could not be located in capabilities.")
            return False
        
        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.WaitForElementPresence(element=pin[0], displayed=True, time_ms=200.00):
            result &= self.TapElement(self.p_UIElements.cancelPasscode)

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=500.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)

        if self.WaitForElementPresence(element=self.p_UIElements.holdNearIcon, displayed=True, time_ms=200.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label, nb_of_taps=2)
            else:
                result &= self.TapElement(element_to_tap)
                result &= self.TapElement(element_to_tap)
        
        if self.TapByScreenCoverageFromText(elementToFind=self.SmartDeviceConstants.ENTER_PASSCODE):
            if self.WaitForElementPresence(element=self.p_UIElements.confirmAssistiveTouchIcon, displayed=True, time_ms=5000.00):
                result &= self.PerformScreenCoverageSequence(coordinates=[self.p_AssistiveTouch, self.p_PayAssistiveTouch, self.p_ConfirmWithAssistiveTouch])
                if self.IsTextOnScreen(textToMatch=pin[0]):
                    result &= self.TapByScreenCoverageFromText(pin)
                    if self.WaitForElementPresence(element=self.p_UIElements.holdNearIcon, displayed=True, time_ms=1000.00):
                        AddComment("Hold near NFC...")
                        return True
                    
            self.TapByScreenCoverageFromText(elementToFind=self.SmartDeviceConstants.ENTER_PASSCODE)
            if self.IsTextOnScreen(textToMatch=pin[0]):
                result &= self.TapByScreenCoverageFromText(pin)

        if self.WaitForElementPresence(element=self.p_UIElements.confirmAssistiveTouchIcon, displayed=True, time_ms=5000.00):
            result &= self.PerformScreenCoverageSequence(coordinates=[self.p_AssistiveTouch, self.p_PayAssistiveTouch, self.p_ConfirmWithAssistiveTouch])
            if self.IsTextOnScreen(textToMatch=pin[0]):
                result &= self.TapByScreenCoverageFromText(pin)

        if self.WaitForElementPresence(element=self.p_UIElements.holdNearIcon, displayed=True, time_ms=1000.00):
            AddComment("Hold near NFC...")
            result &= True
        else:
            AddComment("Wallet did not reach ready state. Check log files for screen shot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_GetNFCReadyState_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            result &= False

        return result
    
    def UnlockWallet(self, key_buttons: list) -> bool:
        """
        Unlocks the wallet by interacting with the specified key buttons.

        The key_buttons parameter must be a list of complex parameters from the following values:
        - SmartDevice.p_ButtonPasscode.button0
        - SmartDevice.p_ButtonPasscode.button1
        - SmartDevice.p_ButtonPasscode.button2
        - SmartDevice.p_ButtonPasscode.button3
        - SmartDevice.p_ButtonPasscode.button4
        - SmartDevice.p_ButtonPasscode.button5
        - SmartDevice.p_ButtonPasscode.button6
        - SmartDevice.p_ButtonPasscode.button7
        - SmartDevice.p_ButtonPasscode.button8
        - SmartDevice.p_ButtonPasscode.button9

        @param key_buttons: A list of key buttons to interact with for unlocking the wallet.
        @return: `True` if the wallet is unlocked successfully; `False` otherwise.
        """
        result = True
        for digit in key_buttons:
            if self.WaitForElementPresence(element=digit, displayed=True, time_ms=200.00):
                result &= self.TapElement(digit)
            else:
                return False
        return result

    def PerformScreenCoverageSequence(self, coordinates : list = None, animation_delay_time_ms : int = 100) -> bool:
        """
        Performs a sequence of screen coverage actions based on the provided coordinates.

        Examples of what coordinates should be:
        - `<PARM name='p_PayAssistiveTouch' type='STR' value='xP=0.47; yP=0.81; tapCount=1; duration=70'/>`

        @param coordinates: A list of coordinates in form of Complex Parameter representing the screen coverage actions.
        @return: `True` if the sequence is performed successfully; `False` otherwise.
        """
        result = True
        time_for_assistive_menu_to_close = 2000
        coordinates = [coordinates] if not isinstance(coordinates, list) else coordinates
        for coord in coordinates:
            result &= self.TapElementByScreenCoverage(coord.xP, coord.yP, coord.tapCount, coord.duration)
            WaitForDelay(animation_delay_time_ms)
        WaitForDelay(time_for_assistive_menu_to_close)
        return result

    def CheckAccessoryConnection(self, state : int) -> bool:
        """
        Checks the connection status of an accessory.

        The `state` parameter accepts only the following values:
        - `1` for connected (use `SmartDevice.p_AccessoryStates.connected`)
        - `0` for not connected (use `SmartDevice.p_AccessoryStates.notConnected`)

        @param state: The expected connection status of the accessory.
        @return: `True` if the accessory matches the expected connection status; `False` otherwise.
        """
        result = True
        if state not in (0, 1):
            raise ValueError("Status must be 0 (not connected) or 1 (connected).")
        if self.StartApp(app=self.p_BundleIds.Settings):
            if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_UIElements.backButton)

            if self.WaitForElementPresence(element=self.p_UIElements.settingsButton, displayed=True, time_ms=2000.00):
                self.TapElement(self.p_UIElements.settingsButton)

            self.SwipeDown(repeat_count=2, back_interval_ms=200.00)
            if self.WaitForElementPresence(element=self.p_UIElements.bluetoothButton, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_UIElements.bluetoothButton)

                if self.WaitForElementPresence(element=self.p_UIElements.accessory, displayed=True, time_ms=5000.00):
                    expected_element = self.p_UIElements.accessoryConnectedStateText if state == 1 else self.p_UIElements.accessoryNotConnected
                    
                    if self.WaitForElementPresence(element=expected_element, displayed=True, time_ms=2000.00):
                        AddComment("Accessory connection reached expected state.")
                        result &= True
                    else:
                        AddComment("Accessory not in expected state.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckAccessoryConnection_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        result &= False
                else:
                    AddComment("Accessory not present on screen.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckAccessoryConnection_{datetime.now():%Y_%m_%d_%H_%M}.png")
                    result &= False
            else:
                AddComment("Bluetooth button not accessible.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckAccessoryConnection_{datetime.now():%Y_%m_%d_%H_%M}.png")
                result &= False
        else:
            AddComment("Settings icon not found.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckAccessoryConnection_{datetime.now():%Y_%m_%d_%H_%M}.png")
            result &= False

        if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=3000.00):
            result &= self.TapElement(self.p_UIElements.backButton)

        if self.WaitForElementPresence(element=self.p_UIElements.settingsButton, displayed=True, time_ms=2000.00):
            self.TapElement(self.p_UIElements.settingsButton)

        if not self.StartApp(app=self.p_BundleIds.Wallet):
            return False
        return result

    def PressLockButton(self, verifyActionCompleted = False, dk_label : str = None, dk_xpath : str = None) -> bool:
        """
        Presses the lock button in the Wallet UI to lock the vehicle, with optional verification and flexible key selection.

        This method automates the process of locking the vehicle via the Wallet app on an iPhone. It supports tapping the lock button either by visible text (using OCR) or by a provided XPath, and can verify that the vehicle has reached the locked state.

        Parameters:
            verifyActionCompleted (bool, optional):
                If True (default), checks that the vehicle is actually locked after pressing the button by verifying the lock state indicator.
                If False, skips this verification step.
            dk_label (str, optional):
                The visible text label of the digital key (DK) to tap. If provided, the method uses OCR to find and tap the key by text.
                If not provided, the method uses the element specified by dk_xpath or defaults to the car model key element.
            dk_xpath (str, optional):
                The XPath of the DK element to tap. Used only if dk_label is not provided.

        Returns:
            bool: True if the lock action was performed successfully (and verified if requested), False otherwise.

        Process:
            - If the add card button is present, taps the DK (by label or XPath).
            - Checks for lock/unlock button availability and state indicators.
            - Taps the lock button if available and verifies the locked state if requested.
            - Logs comments and screenshots for error or unexpected states.
        """
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)

        if self.WaitForElementPresence(element=self.p_CarModelButtons.carModelKeyLockUnlockNotAvailable, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Lock button is not available. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressLockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        elif verifyActionCompleted and self.WaitForElementPresence(element=self.p_Indicators.lockStateIndicator, displayed=True, time_ms=1000.00):
            result &= True
            AddComment("Vehicle is already in locked state. Check log files for screenshot of the device.")

        elif not self.WaitForElementPresence(element=self.p_CarModelButtons.carModelKeyLockUnlock, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Lock button is not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressLockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        else:
            result &= self.TapElement(self.p_CarModelButtons.carModelKeyLockUnlock)
            if not result:
                AddComment("Lock button not pressed. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_PressLockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")
            if verifyActionCompleted:
                if self.WaitForElementPresence(element=self.p_Indicators.lockStateIndicator, displayed=True, time_ms=5000.00):
                    result &= True
                else:
                    result &= False
                    AddComment("Vehicle did not reach locked state. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_PressLockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def PressUnlockButton(self, verifyActionCompleted = False, dk_label : str = None, dk_xpath : str = None) -> bool:
        """
        Presses the unlock button in the UI and optionally verifies that the vehicle is unlocked.

        The method attempts to locate the unlock button in the following priority order:
            1. By label (dk_label), if provided.
            2. By XPath (dk_xpath), if dk_label is not provided.
            3. Falls back to a default UI element reference if both dk_label and dk_xpath are None.

        Parameters:
            verifyActionCompleted (bool): If True, performs a check to confirm the vehicle was successfully unlocked.
            dk_label (str, optional): Label of the UI element to press. Takes highest priority if provided.
            dk_xpath (str, optional): XPath of the UI element to press. Used if dk_label is not provided.

        Returns:
            bool: True if the unlock action was successful (and verified if requested), False otherwise.
        """
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)    
            else:   
                result &= self.TapElement(element_to_tap)

        if self.WaitForElementPresence(element=self.p_CarModelButtons.carModelKeyLockUnlockNotAvailable, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Unlock button is not available. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressUnlockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        elif verifyActionCompleted and self.WaitForElementPresence(element=self.p_Indicators.unlockStateIndicator, displayed=True, time_ms=1000.00):
            result &= True
            AddComment("Vehicle is already in unlocked state. Check log files for screenshot of the device.")

        elif not self.WaitForElementPresence(element=self.p_CarModelButtons.carModelKeyLockUnlock, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Unlock button is not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressUnlockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        else:
            result &= self.TapElement(self.p_CarModelButtons.carModelKeyLockUnlock)
            if not result:
                AddComment("Unlock button not pressed. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_PressUnlockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")
            if verifyActionCompleted:
                if self.WaitForElementPresence(element=self.p_Indicators.unlockStateIndicator, displayed=True, time_ms=5000.00):
                    result &= True
                else:
                    result &= False
                    AddComment("Vehicle did not reach unlocked state. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_PressUnlockButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def PressPanicButton(self, verifyActionCompleted = False, dk_label : str = None, dk_xpath : str = None) -> bool:
        """
        Presses the panic button in the UI to activate the vehicle's panic alarm, and optionally verifies activation.

        The method attempts to locate the panic button in the following priority order:
            1. By label (dk_label), if provided.
            2. By XPath (dk_xpath), if dk_label is not provided.
            3. Falls back to a default UI element reference if both dk_label and dk_xpath are None.

        Parameters:
            verifyActionCompleted (bool): If True, performs a check to confirm the panic alarm was successfully activated.
            dk_label (str, optional): Label of the UI element to press. Takes highest priority if provided.
            dk_xpath (str, optional): XPath of the UI element to press. Used if dk_label is not provided.

        Returns:
            bool: True if the panic alarm was activated (and verified if requested), False otherwise.
        """
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)

        if self.WaitForElementPresence(element=self.p_CarModelButtons.carModelPanicNotAvailable, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Panic button is not available. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressPanicButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        elif not self.WaitForElementPresence(element=self.p_CarModelButtons.carModelPanic, displayed=True, time_ms=5000.00):
            result &= False
            AddComment("Panic button is not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressPanicButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        else:
            result &= self.TapElement(self.p_CarModelButtons.carModelPanic)
            if not result:
                AddComment("Panic button not pressed. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_PressPanicButton_{datetime.now():%Y_%m_%d_%H_%M}.png")
            if verifyActionCompleted:
                if self.WaitForElementPresence(element=self.p_Indicators.alarmTriggeredStateIndicator, displayed=True, time_ms=1000.00):
                    result &= True
                    AddComment("Alarm activated.")
                elif self.WaitForElementPresence(element=self.p_Indicators.alarmOffStateIndicator, displayed=True, time_ms=1000.00):
                    result &= True
                    AddComment("Alarm stopped.")
                else:
                    result &= False
                    AddComment("Panic did not reach expected state. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_PressPanicButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def PressTrunkButton(self, verifyActionCompleted = False, dk_label : str = None, dk_xpath : str = None) -> bool:
        """
        Presses the trunk button in the UI to open the vehicle's trunk, and optionally verifies that it was opened.

        The method attempts to locate the trunk button in the following order of priority:
            1. By label (dk_label), if provided.
            2. By XPath (dk_xpath), if dk_label is not provided.
            3. Falls back to a default UI element reference (carModelKey) if both dk_label and dk_xpath are None.

        Parameters:
            verifyActionCompleted (bool): If True, performs a check to confirm the trunk was successfully opened.
            dk_label (str, optional): Label of the UI element to press. Takes highest priority if provided.
            dk_xpath (str, optional): XPath of the UI element to press. Used if dk_label is not provided.

        Returns:
            bool: True if the trunk was opened (and verified if requested), False otherwise.
        """
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)

        if self.WaitForElementPresence(element=self.p_CarModelButtons.carModelTrunkNotAvailable, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Trunk button is not available. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressTrunkButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        elif not self.WaitForElementPresence(element=self.p_CarModelButtons.carModelTrunk, displayed=True, time_ms=1000.00):
            result &= False
            AddComment("Trunk button is not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_PressTrunkButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        else:
            result &= self.TapElement(self.p_CarModelButtons.carModelTrunk)
            if not result:
                AddComment("Trunk button not pressed. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_PressTrunkButton_{datetime.now():%Y_%m_%d_%H_%M}.png")
            if verifyActionCompleted:
                if self.WaitForElementPresence(element=self.p_Indicators.trunkOpenedStateIndicator, displayed=True, time_ms=15000.00):
                    AddComment("Trunk opened successfully.")
                    result &= True
                elif self.WaitForElementPresence(element=self.p_Indicators.trunkClosedStateIndicator, displayed=True, time_ms=15000.00):
                    AddComment("Trunk closed successfully.")
                    result &= True
                else:
                    result &= False
                    AddComment("Trunk did not reach expected state. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_PressTrunkButton_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def CheckVehicleState(self, state: int,  dk_label : str = None, dk_xpath : str = None) -> bool:
        """
        Verifies if the vehicle is in the expected state by checking the appropriate UI element.

        The method attempts to locate the UI element representing the vehicle state in the following priority order:
            1. By label (dk_label), if provided.
            2. By XPath (dk_xpath), if dk_label is not provided.
            3. Falls back to a default UI element reference if both dk_label and dk_xpath are None.

        Supported values for `state`:
            - 0: unlocked         (<SmartDevice>.p_RKEStates.unlocked)
            - 1: locked           (<SmartDevice>.p_RKEStates.locked)
            - 2: alarm triggered  (<SmartDevice>.p_RKEStates.alarmTriggered)
            - 3: alarm off        (<SmartDevice>.p_RKEStates.alarmOff)
            - 4: trunk opened     (<SmartDevice>.p_RKEStates.trunkOpened)
            - 5: trunk closed     (<SmartDevice>.p_RKEStates.trunkClosed)

        Parameters:
            state (int): Expected vehicle state (values 0 through 5).
            dk_label (str, optional): Label of the UI element to verify. Takes highest priority if provided.
            dk_xpath (str, optional): XPath of the UI element to verify. Used if dk_label is not provided.

        Returns:
            bool: True if the vehicle reaches the expected state, False otherwise.

        Raises:
            ValueError: If `state` is not one of the supported values (0â€“5).
        """

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        state_map = {
            0: self.p_Indicators.unlockStateIndicator,
            1: self.p_Indicators.lockStateIndicator,
            2: self.p_Indicators.alarmTriggeredStateIndicator,
            3: self.p_Indicators.alarmOffStateIndicator,
            4: self.p_Indicators.trunkOpenedStateIndicator,
            5: self.p_Indicators.trunkClosedStateIndicator
        }

        if state not in state_map:
            raise ValueError(
                                f"Invalid state: {state}. Must be one of the following:\n"
                                f"  0 - unlocked\n"
                                f"  1 - locked\n"
                                f"  2 - alarm triggered\n"
                                f"  3 - alarm off\n"
                                f"  4 - trunk opened\n"
                                f"  5 - trunk closed"
                            )
        result = True
    
        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)
    
        expected_element = state_map[state]
        
        if self.WaitForElementPresence(element=expected_element, displayed=True, time_ms=1000.00):
            result &= True
        else:
            result &= False
            AddComment(f"Vehicle did not reach the expected state. Check log files for a screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckVehicleState_{datetime.now():%Y_%m_%d_%H_%M}.png")
    
        return result

    def CheckButtonAvailability(self, button : str, availability : bool, dk_label : str = None, dk_xpath : str = None) -> bool:
        """
        Checks the availability of a specific RKE button on the device.

        The method performs the following steps:
            1. Verifies that the "Add Card" button is present.
            2. Attempts to tap the car model key element, determined in the following priority order:
                - By label (dk_label), if provided.
                - By XPath (dk_xpath), if dk_label is not provided.
                - Falls back to a default UI element if both are None.
            3. Checks whether the specified `button` is present and in the expected availability state.

        Parameters:
            button (str): The identifier of the UI button to check.
            availability (bool): Expected availability state (`True` for active, `False` for inactive).
            dk_label (str, optional): Label of the UI element to tap. Takes highest priority if provided.
            dk_xpath (str, optional): XPath of the UI element to tap. Used if dk_label is not provided.

        Returns:
            bool: `True` if the button is found and matches the expected state; `False` otherwise.

        Additional Actions:
            - Captures a screenshot if the button is missing or does not match the expected state.
            - Logs a comment when tapping the car model key fails or when the button is not in the expected state.
        """
        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                if not self.TapByScreenCoverageFromText(dk_label):
                    AddComment("Failed to tap the car model key.")
                    return False
            else:
                if not self.TapElement(element_to_tap):
                    AddComment("Failed to tap the car model key.")
                    return False

        if not self.WaitForElementPresence(button, displayed=True, time_ms=1000.00):
            AddComment(f"Button could not be located on the screen.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckButtonAvailability_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False

        if not self.CheckElementEnabled(element=button, displayed=availability):
            AddComment(f"Button is not in the expected state: {'Enabled' if availability else 'Disabled'}.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_CheckButtonAvailability_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False

        return True

    def FriendKeySharing(self, pin: list = None, apple_id_owner: str = None, apple_id_friend: str = None, friend: SmartDevice = None, dk_label: str = None, dk_xpath: str = None, friend_device_name: str = None) -> bool:
        '''
        Shares a digital car key with a friend using iMessage or AirDrop, depending on the iOS version.

        This method determines the sharing mechanism based on the recipient device's iOS version:
        - For iOS versions earlier than 18.0, it uses iMessage.
        - For iOS 18.0 and above, it uses AirDrop.

        The method first retrieves the passcode from device capabilities. If any required capability is missing,
        the method logs the issue and returns False. Based on the iOS version, it then delegates the key-sharing
        process to the appropriate private method (`_friendKeySharingiMessage` or `_friendKeySharingAirDrop`).

        If `friend` is provided, the method will also attempt to perform actions on the recipient's device to
        retrieve the key and confirm that it was successfully added to Wallet. If `friend` is not provided,
        only the sender-side sharing flow is executed, and no operations are performed on the recipient's device.

        @param pin: A list of digits representing the device passcode (fetched internally in this method).
        @param apple_id_owner: (Optional) The Apple ID of the car key owner (sender).
        @param apple_id_friend: (Optional) The Apple ID of the friend receiving the car key.
        @param friend: (Optional) A `SmartDevice` instance representing the friend's device receiving the key.
        @param dk_label: (Optional) A visible label used to identify the car key in the Wallet app.
        @param dk_xpath: (Optional) An XPath used to identify the car key in the Wallet app if no label is provided.

        @return: `True` if the key is shared successfully via the appropriate method; `False` otherwise.
        '''
        result = True

        # Handle 'Done' button if present
        self.TapByScreenCoverageFromText(self.SmartDeviceConstants.DONE_BUTTON)

        if pin is None:
            pin = self._fetchMappedPasscode()
        if pin is None:
            AddComment("Pin could not be located in capabilities.")
            return False

        iOSVersion = self.GetCapability(self.SmartDeviceConstants.iOS_VERSION_CAPABILITY)
        iOSVersion = int(iOSVersion.partition('.')[0])
        if friend_device_name is None:
            friend_device_name = friend.GetCapability(friend.SmartDeviceConstants.DEVICE_NAME_CAPABILITY)

        if iOSVersion is None:
            AddComment("iOS version could not be located in capabilities.")
            return False
        
        if float(iOSVersion) < 18.0:
            result &= self._friendKeySharingiMessage(apple_id_owner, apple_id_friend, pin, dk_label=dk_label, dk_xpath=dk_xpath, friend=friend)
            if not result:
                AddComment("Failed to share key via iMessage. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
        else:
            result &= self._friendKeySharingAirDrop(friend_device_name, pin, dk_label=dk_label, dk_xpath=dk_xpath, friend=friend)
            if not result:
                AddComment("Failed to share key via AirDrop. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def _friendKeySharingAirDrop(self, friend_device_name: str, pin: list, friend: SmartDevice = None, dk_label: str = None, dk_xpath: str = None) -> bool:
        '''
        Shares a digital car key with a friend using AirDrop and (optionally) confirms that the key is successfully added on the friend's device.

        This method handles the AirDrop-based car key sharing flow, including Wallet UI navigation, initiating the AirDrop transfer,
        and confirming key permissions via AssistiveTouch if needed. If a `friend` device is provided, it will also attempt
        to enable AirDrop on the friend's device and verify that the key was received and added to Wallet.

        If `friend` is not provided, only the key-sharing process from the sender's side is performed. No actions will be taken
        on the recipient device (e.g., enabling AirDrop or verifying Wallet key presence).

        @param friend_device_name: The AirDrop name of the friend's device.
        @param pin: The device's passcode digits used to confirm the action (as a list of strings).
        @param friend: (Optional) A `SmartDevice` instance representing the recipient's device. Required for enabling AirDrop and confirming key reception.
        @param dk_label: (Optional) A label string used to visually identify the key in the Wallet app.
        @param dk_xpath: (Optional) An XPath selector used to identify the key in Wallet if `dk_label` is not provided.

        @return: `True` if the key is successfully shared and (if applicable) confirmed as added on the friend's device; `False` otherwise.
                Logs screenshots and failure comments at each key step for traceability.
        '''
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey 

        if dk_label:
            if not self.IsTextOnScreen(dk_label):
                AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False
        else:
            if not self.WaitForElementPresence(element=element_to_tap, displayed=True, time_ms=2000):
                AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)
        else:
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label, nb_of_taps=2)
            else:
                result &= self.TapElement(element_to_tap)
                result &= self.TapElement(element_to_tap)

        if friend:
            # activate Airdrop on friend 
            result &= friend.SetAirdropState(state=1)
        
        if self.WaitForElementPresence(element=self.p_UIElements.shareKeyButton, displayed=True, time_ms=10000.00):
            result &= self.TapElement(self.p_UIElements.shareKeyButton)

            if self.WaitForElementPresence(element=self.p_WalletElements.airDropIcon, displayed=True, time_ms=15000.00):
                result &= self.TapElement(self.p_WalletElements.airDropIcon)

                if self.TapByScreenCoverageFromText(elementToFind=friend_device_name, timeout=15000):

                    if self.WaitForElementPresence(element=self.p_UIElements.keyPermissions, displayed=True, time_ms=10000.00):
                        result &= self.TapElement(self.p_UIElements.dkNoPasscodeSwitch)
                        result &= self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CONTINUE_BUTTON)
                        if self.IsTextOnScreen(textToMatch=self.SmartDeviceConstants.CONFIRM_WITH_ASSISTIVE_TOUCH, timeout=20000, use_ss_as_backup=True):
                            result &= self.PerformScreenCoverageSequence(coordinates=[self.p_AssistiveTouch, self.p_PayAssistiveTouch, self.p_ConfirmWithAssistiveTouch])
                            if self.TapByScreenCoverageFromText(pin, skipIfNotFound=False, use_ss_as_backup=True):
                                if friend:
                                    result &= friend.AddReceivedAirDropDKToWallet(dk_label=dk_label, dk_xpath=dk_xpath)
                            else:
                                AddComment("Passcode could not be located on screen. Check log files for screenshot of the device.")
                                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                return False

                            if self.IsTextOnScreen(textToMatch=self.SmartDeviceConstants.CANNOT_ADD_MESSAGE):
                                AddComment("Cannot send message appeared on the screen. Check log files for screenshot of the device.")
                                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                self.TapByScreenCoverageFromText(self.SmartDeviceConstants.OK_BUTTON)
                                self.TapByScreenCoverageFromText(self.SmartDeviceConstants.SETUP_LATER_BUTTON)
                                self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CANCEL)
                                self.TapElement(name=self.p_UIElements.closeButton)
                                return False
                        else:
                            AddComment("Confirm with assistive touch could not be located on screen. Check log files for screenshot of the device.")
                            self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                            return False
                    else:
                        AddComment("Friend device name not found in Airdrop menu. Check log files for screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        return False
                else:
                    result &= False
                    AddComment("Key permisions not present on screen. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                            
            else:
                AddComment("AirDrop icon not present in share menu. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False
        else:
            AddComment("Share button not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False

        return result

    def _friendKeySharingiMessage(self, apple_id_owner: str, apple_id_friend: str, pin: list, friend: SmartDevice = None, dk_label: str = None, dk_xpath: str = None) -> bool:
        '''
        Shares a digital car key with a friend via iMessage and optionally confirms that the key is successfully added on the friend's device.

        This method performs the key-sharing workflow using the Wallet app, selecting iMessage as the delivery method,
        entering the friend's Apple ID, and handling screen interactions including optional AssistiveTouch authentication.
        If the sharing flow completes successfully and a `friend` device is provided, the method continues by calling
        `AddiMessageKeyToWallet` on the friend's device to retrieve the key from the iMessage and validate that it was added to Wallet.

        If `friend` is not provided, only the sending side of the iMessage key-sharing flow is executed. No operations
        are performed on the recipient's device to retrieve or confirm the key.

        @param apple_id_owner: The Apple ID of the key owner (sender).
        @param apple_id_friend: The Apple ID of the friend receiving the key via iMessage.
        @param pin: A list of digits representing the passcode used for authentication (e.g. device unlock/passcode).
        @param friend: (Optional) A `SmartDevice` instance representing the friend's device. Required for retrieving and confirming the key on the recipient's side.
        @param dk_label: (Optional) A label string used to identify the car key in Wallet by visible text.
        @param dk_xpath: (Optional) An XPath string used to identify the car key in Wallet if `dk_label` is not available.

        @return: `True` if the key is successfully shared and (if applicable) added on the friend's device; `False` otherwise.
                All failure points log screenshots and comments for debugging purposes.
        '''
        result = True 

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if dk_label:
            if not self.TapByScreenCoverageFromText(dk_label):
                AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False
        else:
            if not self.WaitForElementPresence(element=element_to_tap, displayed=True, time_ms=2000):
                AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False

        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=1000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)
        else:
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label, nb_of_taps=2)
            else:
                result &= self.TapElement(element_to_tap)
                result &= self.TapElement(element_to_tap)

        if self.WaitForElementPresence(element=self.p_UIElements.shareKeyButton, displayed=True, time_ms=2000.00):
            result &= self.TapElement(self.p_UIElements.shareKeyButton)

            if self.WaitForElementPresence(element=self.p_MessagingElements.iMessageWalletShare, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_MessagingElements.iMessageWalletShare)

                if self.WaitForElementPresence(element=self.p_UIElements.keyPermissions, displayed=True, time_ms=10000.00):
                    result &= self.TapElement(self.p_UIElements.continueButton)

                if self.WaitForElementPresence(element=self.p_UIElements.confirmButton, displayed=True, time_ms=2000.00):
                    result &= self.TapElement(self.p_UIElements.confirmButton)

                if self._typeInAppleId(apple_id_friend):
                    if not self.TapElement(self.p_MessagingElements.returnCreateMessage):
                        AddComment("Return button not present on screen.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        return False                            
                else:
                    AddComment("Could not enter apple id.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                    return False

                if self.WaitForElementPresence(element=self.p_UIElements.sendMessageButton, displayed=True, time_ms=5000.00):
                    result &= self.TapElement(self.p_UIElements.sendMessageButton)

                    if self.WaitForElementPresence(element=self.p_UIElements.continueWithoutSecurity, displayed=True, time_ms=5000.00):
                        result &= self.TapElement(self.p_UIElements.continueWithoutSecurity)

                    if self.WaitForElementPresence(element=self.p_UIElements.continueWithoutSecurity, displayed=True, time_ms=5000.00):
                        result &= self.TapElement(self.p_UIElements.continueWithoutSecurity)

                    else:
                        if not self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CONTINUE_ANYWAY):
                            AddComment("The 'Continue' button could not be located on screen. Mapping might be wrong or element missing. Check log files for screenshot of the device.")
                            self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                            return False

                        if self.WaitForElementPresence(element=self.p_UIElements.confirmButton, displayed=True, time_ms=3000.00):
                            result &= self.PerformScreenCoverageSequence(coordinates=[self.p_AssistiveTouch, self.p_PayAssistiveTouch, self.p_ConfirmWithAssistiveTouch])
                            if self.IsTextOnScreen(textToMatch=pin[0]):
                                result &= self.TapByScreenCoverageFromText(pin, skipIfNotFound=False)
                            else:
                                AddComment("Passcode could not be located on screen. Check log files for screenshot of the device.")
                                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                return False
                        else:
                            if self.IsTextOnScreen(textToMatch=self.SmartDeviceConstants.CONFIRM_WITH_ASSISTIVE_TOUCH):
                                result &= self.PerformScreenCoverageSequence(coordinates=[self.p_AssistiveTouch, self.p_PayAssistiveTouch, self.p_ConfirmWithAssistiveTouch])
                                if self.IsTextOnScreen(textToMatch=pin[0]):
                                    result &= self.TapByScreenCoverageFromText(pin, skipIfNotFound=False)
                                    if friend:
                                        result &= friend.AddReceivediMessageDKToWallet(apple_id_to_receive_key_from=apple_id_owner, dk_label=dk_label, dk_xpath=dk_xpath)
                                else:
                                    AddComment("Passcode could not be located on screen. Check log files for screenshot of the device.")
                                    self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                    return False

                                if self.IsTextOnScreen(self.SmartDeviceConstants.CANNOT_ADD_MESSAGE):
                                    AddComment("Cannot send message appeared on the screen. Check log files for screenshot of the device.")
                                    self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                    self.TapByScreenCoverageFromText(self.SmartDeviceConstants.OK_BUTTON)
                                    self.TapByScreenCoverageFromText(self.SmartDeviceConstants.SETUP_LATER_BUTTON)
                                    self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CANCEL)
                                    self.TapElement(name=self.p_UIElements.closeButton)
                                    return False
                            else:
                                AddComment("Confirm with assistive touch could not be located on screen. Check log files for screenshot of the device.")
                                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                return False
                else:
                    result &= False
                    AddComment("Send message button not present on screen. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                            
            else:
                AddComment("iMessage not present in share menu. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False
        else:
            AddComment("Share button not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_FriendKeySharing_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False

    def AddReceivedAirDropDKToWallet(self, dk_label: str = None, dk_xpath: str = None, verify_is_completed: bool = True) -> bool:
        '''
        Completes the process of adding a digital car key received via AirDrop to the Wallet app on the current device.

        The method begins by tapping the "Accept" button for the incoming key transfer, then proceeds to tap
        the "Add Car Key" button. If `verify_is_completed` is enabled, it further verifies that the key
        has been successfully added to the Wallet app.

        Verification can be done either by locating a specific label (`dk_label`) or by checking for a UI element
        identified by `dk_xpath`. If neither is provided, a default Wallet element is used for confirmation.

        @param dk_label: (Optional) A label string used to identify the car key in Wallet via visible text.
        @param dk_xpath: (Optional) An XPath selector to identify the car key element if `dk_label` is not used.
        @param verify_is_completed: Whether to launch Wallet and verify that the key was successfully added.

        @return: `True` if the key is successfully accepted and verified (if requested); `False` otherwise.
                Logs screenshots and comments at all failure points.
        '''
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        result &= self.TapByScreenCoverageFromText(self.SmartDeviceConstants.ACCEPT_BUTTON, timeout=25000, use_only_ss=True)
        if not result:
            AddComment("Accept button not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_AddReceivedAirDropDKToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False
        
        result &= self.TapByScreenCoverageFromText(self.SmartDeviceConstants.ADD_CAR_KEY, timeout=40000, use_only_ss=True)
        if not result:
            AddComment("Add Car Key button not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_AddReceivedAirDropDKToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False

        result &= self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CONTINUE_BUTTON, timeout=60000)
        if not result:
            AddComment("Continue button not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_AddReceivedAirDropDKToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False
            
        if verify_is_completed:
            if self.StartApp(app=self.p_BundleIds.Wallet):
                if dk_label:
                    if not self.IsTextOnScreen(dk_label):
                        AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AddReceivedAirDropDKToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        return False
                    else:
                        result &= True
                else:
                    if not self.WaitForElementPresence(element=element_to_tap, displayed=True, time_ms=2000):
                        AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AddReceivedAirDropDKToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        return False
                    else:
                        result &= True
        return result

    def AddReceivediMessageDKToWallet(self, apple_id_to_receive_key_from: str, dk_label: str = None, dk_xpath: str = None, verify_is_completed: bool = True) -> bool:
        '''
        Adds a car key received via iMessage to the Wallet app on the current device.

        This method launches the Messages app, searches for a message from the specified Apple ID,
        taps the "Add Car Key" button, and continues through the Wallet app flow to finalize the key addition.

        If `verify_is_completed` is enabled, the method also launches the Wallet app to verify that
        the key was successfully added. Verification is done either by locating a label (`dk_label`),
        an XPath element (`dk_xpath`), or falling back to a default Wallet UI element.

        @param apple_id_to_receive_key_from: The Apple ID from which the car key is expected to be received.
        @param dk_label: (Optional) A visible label to identify the car key in the Wallet app.
        @param dk_xpath: (Optional) An XPath selector used to locate the key element in Wallet if `dk_label` is not provided.
        @param verify_is_completed: If `True`, launches the Wallet app and verifies that the key was added successfully.

        @return: `True` if the key is added (and verified, if requested); `False` otherwise. Logs screenshots and comments on failure.
        '''
        result = True

        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        if self.StartApp(app=self.p_BundleIds.Messages):

            if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_UIElements.backButton)

            self.SwipeDown(repeat_count=2, back_interval_ms=200.00)

            if self.WaitForElementPresence(element=apple_id_to_receive_key_from, displayed=True, time_ms=2000.00):
                result &= self.TapElement(apple_id_to_receive_key_from)

                if self.WaitForElementPresence(element=self.p_MessagingElements.addCarKeyButton, displayed=True, time_ms=10000.00):
                    result &= self.TapElement(self.p_MessagingElements.addCarKeyButton)

                    if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=6000.00):
                        result &= self.TapElement(self.p_UIElements.addCardButton)

                        if self.WaitForElementPresence(element=self.p_UIElements.confirmButton, displayed=True, time_ms=20000.00):
                            result &= self.TapElement(self.p_UIElements.confirmButton)

                            if verify_is_completed:
                                if dk_label:
                                    if not self.TapByScreenCoverageFromText(dk_label):
                                        AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                        return False
                                else:
                                    if not self.WaitForElementPresence(element=element_to_tap, displayed=True, time_ms=2000):
                                        AddComment("Car model key not present in wallet. Check log files for screenshot of the device.")
                                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                        return False
                        else:
                            result &= False
                            AddComment("Continue button not present on screen. Check log files for screenshot of the device.")
                            self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
                    else:
                        result &= False
                        AddComment("Add car key button not present on screen. Check log files for screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
                else:
                    result &= False
                    AddComment("Add car key button not present in message. Check log files for screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
            else:
                result &= False
                AddComment(f"No message received from specified Apple ID. Check log files for screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")
        else:
            result &= False
            AddComment("Messages app not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_AddiMessageKeyToWallet_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def _typeInAppleId(self, apple_id: str, append: bool = False) -> bool:
        '''
        Enters the Apple ID into a text field.

        @param apple_id: The Apple ID string to be entered.
        @param append: Whether to append the text or replace it.
        @return: `True` if the Apple ID is entered successfully; `False` otherwise.
        '''
        result = True

        if self.WaitForElementPresence(element=self.p_UIElements.emailPlaceholder, displayed=True, time_ms=20000.00):
            result &= self.SetElementText(self.p_UIElements.emailPlaceholder, apple_id, append)
        else:
            result &= False
            AddComment("Email placeholder not present on screen. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_TypeAppleId_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def CheckCarKeyPresence(self, dk_label: str = None, dk_xpath: str = None, is_present: bool = True) -> bool:
        '''
        Checks whether a car key is present or absent in the Wallet app by verifying either a visible text label or an XPath.

        Priority is given to the `dk_label` parameter if provided. If the label is not visible on screen,
        the method will attempt to check using the `dk_xpath`. If neither are provided or found, it falls
        back to default Wallet UI elements for verification. The `is_present` parameter determines whether
        to check for the presence (True) or absence (False) of the car key.

        Parameters:
            dk_label (str, optional): An optional label identifying the Device Key (DK) to be used.
                                    This should be a visible text string shown in the Wallet UI.
                                    Takes priority over `dk_xpath` if both are given.
            dk_xpath (str, optional): An optional XPath to locate the DK element in the Wallet UI.
                                    Used only if `dk_label` is not provided or not found.
            is_present (bool, optional): If True, checks for the presence of the car key; if False, checks for its absence.
                                        Defaults to True.

        Returns:
            bool: True if the condition is met (key is present when is_present=True, or key is absent when is_present=False);
                False otherwise.
        '''
        screenshot_name = f"{Prepare._tcName}_CheckCarKeyPresence_{datetime.now():%Y_%m_%d_%H_%M}.png"

        key_detected = False

        if dk_label:
            key_detected = self.IsTextOnScreen(self.p_CarModelKeyLabel.carModelKeyLabel)
        elif dk_xpath:
            key_detected = self.WaitForElementPresence(element=dk_xpath, displayed=True, time_ms=2000.00)
        else:
            key_detected = (
                self.IsTextOnScreen(self.p_CarModelKeyLabel.carModelKeyLabel) or
                self.WaitForElementPresence(element=self.p_WalletElements.carModelKey, displayed=True, time_ms=2000.00)
            )

        result = key_detected if is_present else not key_detected

        if not result:
            AddComment(f"Car model key {'not present' if is_present else 'present'} in wallet. Check log files for screenshot of the device.")
            self.LogDeviceScreenShot(screenshot_name)

        return result

    def DeleteCarModelKey(self, dk_label: str = None, dk_xpath: str = None) -> bool:
        '''
        Deletes a car model key from the Wallet app.

        Parameters:
            dk_label (str, optional): An optional label identifying the Device Key (DK) to be used.
                                    This should be a visible text string shown in the Wallet UI.
                                    Takes priority over `dk_xpath` if both are given.

            dk_xpath (str, optional): An optional XPath to locate the DK element in the Wallet UI.
                                    Used only if `dk_label` is not provided.

        @return: `True` if the key is deleted successfully; `False` otherwise.
        '''
        result = True
        dk_label = str(dk_label) if dk_label else (self.p_CarModelKeyLabel.carModelKeyLabel if self.p_CarModelKeyLabel.carModelKeyLabel != "UNDEFINED" else None)
        element_to_tap = dk_xpath if dk_xpath else self.p_WalletElements.carModelKey

        # Handle 'Continue' button if present
        self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CONTINUE_BUTTON)
        
        # Handle 'OK' button if present
        self.TapByScreenCoverageFromText(self.SmartDeviceConstants.OK_BUTTON)
        
        # Check if the car model key is already missing
        if dk_label:
            if not self.IsTextOnScreen(dk_label):
                AddComment("Car key model already missing from the wallet.")
                return True
        elif dk_xpath:
            if not self.WaitForElementPresence(element=dk_xpath, displayed=True, time_ms=2000.00):
                AddComment("Car key model already missing from the wallet.")
                return True
        else:
            if not self.WaitForElementPresence(element=element_to_tap, displayed=True, time_ms=2000.00) and not self.IsTextOnScreen(textToMatch=self.p_CarModelKeyLabel.carModelKeyLabel):
                AddComment("Car key model already missing from the wallet.")
                return True

        # Tap on the car model key if the 'Add Card' button is present
        if self.WaitForElementPresence(element=self.p_UIElements.addCardButton, displayed=True, time_ms=500.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label)
            else:
                result &= self.TapElement(element_to_tap)

        # Ensure car key options are visible
        if not self.WaitForElementPresence(element=self.p_WalletElements.carModelKeyOptions, displayed=True, time_ms=4000.00):
            if dk_label:
                result &= self.TapByScreenCoverageFromText(dk_label, nb_of_taps=2)
            else:
                result &= self.TapElement(element_to_tap)
                result &= self.TapElement(element_to_tap)

        # Access car key options
        if self.WaitForElementPresence(element=self.p_WalletElements.carModelKeyOptions, displayed=True, time_ms=4000.00):
            result &= self.TapElement(self.p_WalletElements.carModelKeyOptions)

            # Handle car key removal process
            if self.WaitForElementPresence(element=self.p_WalletElements.removeCarKeyButton, displayed=True, time_ms=4000.00):
                result &= self.TapElement(self.p_WalletElements.removeCarKeyButton)
                if self.WaitForElementPresence(element=self.p_WalletElements.removeCarConfirmation, displayed=True, time_ms=4000.00):
                    result &= self.TapElement(self.p_WalletElements.removeCarConfirmation)
                    
                    if dk_label:
                        if not self.IsTextOnScreen(dk_label):
                            result &= True
                    elif dk_xpath:
                        if not self.WaitForElementPresence(element=dk_xpath, displayed=True, time_ms=2000.00):
                            result &= True
                    elif not self.WaitForElementPresence(element=self.p_WalletElements.carModelKey, displayed=True, time_ms=2000.00) and not self.IsTextOnScreen(self.p_CarModelKeyLabel.carModelKeyLabel):
                        result &= True
                else:
                    result &= False
                    AddComment("Remove car key pop-up not present on screen. Check log files for a screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_DeleteCarModelKey_{datetime.now():%Y_%m_%d_%H_%M}.png")
            else:
                result &= False
                AddComment("Remove car key button not present on screen. Check log files for a screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_DeleteCarModelKey_{datetime.now():%Y_%m_%d_%H_%M}.png")
        else:
            result &= False
            AddComment("Car key options button not present on screen. Check log files for a screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_DeleteCarModelKey_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result 

    def GetCarModelKeyReadyForOP(self, url_link: str = None, password: list = None) -> bool:
        """
        Prepares a car model key for operation using the Notes app and related screen interactions.

        This method automates the steps required to ensure a car model key is ready for use. It handles:
        - Navigating through the necessary UI flow (e.g., tapping 'Continue' and 'OK' buttons).
        - Launching the Notes app and processing any associated URL link if provided.
        - Entering a password if required.
        - Identifying and tapping the correct car key based on either a label or XPath.

        Parameters:
            url_link (str, optional): An optional URL to be processed during the key setup.
            password (list, optional): A list of characters or UI elements representing the password to unlock the Notes app.

        Returns:
            bool: True if the car model key is successfully prepared for operation; False otherwise.
        """
        result = True
        if url_link is None:
            raise ValueError("URL link must be provided.")

        # Handle 'Continue' button if present
        self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CONTINUE_BUTTON)
        
        # Handle 'OK' button if present
        self.TapByScreenCoverageFromText(self.SmartDeviceConstants.OK_BUTTON)

        if self.StartApp(app=self.p_BundleIds.Notes):

            # Handle 'Done' button if present
            self.TapByScreenCoverageFromText(self.SmartDeviceConstants.DONE_BUTTON)

            # Handle 'Back' button if present
            self.TapByScreenCoverageFromText(self.SmartDeviceConstants.BACK)

            # Handle if already in a note
            if self.WaitForElementPresence(element=self.p_UIElements.notesButton, displayed=True, time_ms=1000.00):
                result &= self.TapElement(self.p_UIElements.notesButton)

            # Tap 'New Note' button
            if self.WaitForElementPresence(element=self.p_UIElements.newNoteButton, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_UIElements.newNoteButton)

                # Enter mock profile URL in notes text field
                if self.WaitForElementPresence(element=self.p_UIElements.notesTextField, displayed=True, time_ms=2000.00):
                    result &= self.TapElement(self.p_UIElements.notesTextField)
                    result &= self.SetElementText(
                        element=self.p_UIElements.notesTextField,
                        text=url_link,
                        append=False
                    )

                    # Save the note by tapping 'Done'
                    if self.TapByScreenCoverageFromText(self.SmartDeviceConstants.DONE_BUTTON, use_ss_as_backup=True, timeout=20000):

                        # Access the URL link
                        # Try first with logical name (mapped XPath); if not found, fallback to full XPath format
                        if self.WaitForElementPresence(element=url_link, displayed=True, time_ms=6000.00):
                            element_to_tap = url_link
                        elif self.WaitForElementPresence(element=f"(//XCUIElementTypeLink[@name='{url_link}'])[1]", displayed=True, time_ms=6000.00):
                            element_to_tap = f"(//XCUIElementTypeLink[@name='{url_link}'])[1]"
                        else:
                            element_to_tap = None

                        # Access the URL link if any form is found
                        if element_to_tap:
                            tempTapUrlResult = self.TapElement(element_to_tap)

                            if self.WaitForElementPresence(element=element_to_tap, displayed=True, time_ms=6000.00) and not tempTapUrlResult:
                                result &= self.TapElement(element_to_tap)
                            
                            result &= tempTapUrlResult

                            # Tap 'Continue Pairing' button
                            if self.TapByScreenCoverageFromText(self.SmartDeviceConstants.CONTINUE_BUTTON, timeout=20000):
                                if password is not None:
                                    if self.WaitForElementPresence(element=self.p_WalletElements.digitPlaceHolder, displayed=True, time_ms=4000.00):
                                        pin = self._convertPinToKeyDigits(password)
                                        result &= self.UnlockPin(pin)

                                        if self.WaitForElementPresence(element=self.p_SystemPopups.nextButton, displayed=True, time_ms=4000.00):
                                            result &= self.TapElement(self.p_SystemPopups.nextButton)
                                            # Confirm 'Adding Key' label is visible
                                            if self.IsTextOnScreen(self.SmartDeviceConstants.ADDING_KEY_LABEL):
                                                result &= True
                                            else:
                                                result &= False
                                                AddComment("Smart device did not reach pairing state. Check log files for a screenshot of the device.")
                                                self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                        else:
                                            result &= False
                                            AddComment("Next button did not appear on the screen. Check log files for a screenshot of the device.")
                                            self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                    else:
                                        result &= False
                                        AddComment("Enter password did not pop up on the screen. Check log files for a screenshot of the device.")
                                        self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                                else:      
                                    # Confirm 'Adding Key' label is visible
                                    if self.IsTextOnScreen(self.SmartDeviceConstants.ADDING_KEY_LABEL):
                                        result &= True
                                    else:
                                        result &= False
                                        AddComment("Smart device did not reach pairing state. Check log files for a screenshot of the device.")
                                        self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                            else:
                                result &= False
                                AddComment("Continue pairing button not present on screen. Check log files for a screenshot of the device.")
                                self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        else:
                            result &= False
                            AddComment("URL link not present on screen. Check log files for a screenshot of the device.")
                            self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                    else:
                        result &= False
                        AddComment("Done button not present on screen. Check log files for a screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
                else:
                    result &= False
                    AddComment("Notes text field not present on screen. Check log files for a screenshot of the device.")
                    self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
            else:
                result &= False
                AddComment("New note button not present on screen. Check log files for a screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")
        else:
            result &= False
            AddComment("Notes icon app not present on screen. Check log files for a screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_GetCarModelKeyReadyForOP_{datetime.now():%Y_%m_%d_%H_%M}.png")

        return result

    def SetAirplaneMode(self, state : int) -> bool:
        """
        Toggles Airplane on or off via the device's settings.

        This method navigates to the Settings, checks the current Airplane mode state, and toggles it if needed.
        If any step fails, a screenshot is captured, and a comment is logged.

        @param state: Desired Airplane state; `0` for disabled, `1` for enabled.
        @return: `True` if the state is set successfully; `False` otherwise.
        """
        result = True
        
        if state not in [0,1]:
            raise ValueError("The Airplane mode must be 0 (disabled) or 1 (enabled).")

        if not self.StartApp(app=self.p_BundleIds.Settings):
            AddComment(f"Could not turn open Settings on friend device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_SetAirplaneMode_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            return False
        
        # Handle back button inside settings
        if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=2000.00):
            result &= self.TapElement(self.p_UIElements.backButton)
        
        self.SwipeDown(repeat_count=2, back_interval_ms=200.00)
        if self.WaitForElementPresence(element=self.p_UIElements.airplaneModeSwitch, displayed=True, time_ms=2000.00) == True: 
            crtAirplaneState = self.GetElementText(element_name=self.p_UIElements.airplaneModeSwitch)
            if crtAirplaneState is None:
                AddComment("Could not retrieve the Airplane switch value!")
                result &= False  
            else:
                if crtAirplaneState != str(state): 
                    result &= self.TapElement(name=self.p_UIElements.airplaneModeSwitch)
                    if result == True: 
                        AddComment(f"Airplane mode {'disabled' if state == '0' else 'enabled'}")
                    else: 
                        AddComment(f"Could not turn Airplane mode to {'disabled' if state == '0' else 'enabled'}!")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_SetAirplaneMode_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
                        result &= False
                else:
                    AddComment(f"Airplane mode was already {'disabled' if state == '0' else 'enabled'}")
        else:
            AddComment("The Airplane mode switch was not found on the screen !")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_SetAirplaneMode_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.png")
            result &= False
        
        return result
    
    def SetAirdropState(self, state : int) -> bool:
        """
        Toggles Airdrop on or off via the device's settings.

        This method navigates to the Control Center, checks the current Airdrop state, and toggles it if needed.
        If any step fails, a screenshot is captured, and a comment is logged.

        @param state: Desired Airdrop state; `0` for disabled, `1` for enabled.
        @return: `True` if the state is set successfully; `False` otherwise.
        """
        result = True
        
        if state not in [0,1]:
            raise ValueError("The Airdrop mode must be 0 (disabled) or 1 (enabled).")
        
        # Activate Airdrop settings on friend
        if not self.StartApp(app=self.p_BundleIds.Settings):
            AddComment(f"Could not open Settings on friend device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_SetAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False

        self.SwipeDown(repeat_count=1, back_interval_ms=200.00)
        self.SwipeDown(repeat_count=1, back_interval_ms=200.00)

        # Navigate to General > AirDrop
        if self.TapByScreenCoverageFromText(elementToFind=self.SmartDeviceConstants.GENERAL, scroll_if_needed=True, timeout=20000):
            if self.TapByScreenCoverageFromText(elementToFind=self.SmartDeviceConstants.AIRDROP, scroll_if_needed=True, timeout=20000):
                
                # Choose option based on requested state
                if state == 1:  # Enable for everyone
                    if not self.TapByScreenCoverageFromText(elementToFind=self.SmartDeviceConstants.EVERYONE):
                        AddComment("AirDrop option 'Everyone' not found.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AirDrop_EveryoneNotFound_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        return False
                    AddComment("AirDrop set to 'Everyone'")
                elif state == 0:  # Turn off
                    if not self.TapByScreenCoverageFromText(elementToFind=self.SmartDeviceConstants.RECEIVING_OFF):
                        AddComment("AirDrop option 'Receiving Off' not found.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_AirDrop_OffNotFound_{datetime.now():%Y_%m_%d_%H_%M}.png")
                        return False
                    AddComment("AirDrop set to 'Receiving Off'")
                else:
                    AddComment(f"Invalid AirDrop state value: {state}")
                    return False

                # Try navigating back to Settings
                if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=3000.00):
                    self.TapElement(self.p_UIElements.backButton)
                if self.WaitForElementPresence(element=self.p_UIElements.settingsButton, displayed=True, time_ms=2000.00):
                    self.TapElement(self.p_UIElements.settingsButton)

            else:
                AddComment("AirDrop option not found under General.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_AirDrop_NotFound_{datetime.now():%Y_%m_%d_%H_%M}.png")
                return False
        else:
            AddComment("General menu not found in Settings.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_General_NotFound_{datetime.now():%Y_%m_%d_%H_%M}.png")
            return False
        
        return result

    def EnableAirplaneMode(self) -> bool:
        '''
        Enables airplane mode and opens the Wallet app.

        @return: `True` if airplane mode is enabled and Wallet is opened; `False` otherwise.
        '''
        result = True

        if self.StartApp(app=self.p_BundleIds.Settings):

            # Handle back button inside settings
            if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_UIElements.backButton)

            # Scroll to locate airplane mode toggle
            self.SwipeDown(repeat_count=2, back_interval_ms=200.00)

            # Check airplane mode switch presence
            if self.WaitForElementPresence(element=self.p_UIElements.airplaneModeSwitch, displayed=True, time_ms=2000.00):
                if self.GetElementText(self.p_UIElements.airplaneModeSwitch) == "0":
                    result &= self.TapElement(self.p_UIElements.airplaneModeSwitch)

                    # Verify airplane mode is enabled
                    if self.GetElementText(self.p_UIElements.airplaneModeSwitch) == "1":
                        AddComment("Airplane mode enabled.")
                        result &= True
                    else:
                        result &= False
                        AddComment("Airplane mode did not reach enabled state. Check log files for a screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_EnableAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")
            else:
                result &= False
                AddComment("Airplane switch not present on screen. Check log files for a screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_EnableAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")
        else:
            result &= False
            AddComment("Settings app not present on screen. Check log files for a screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_EnableAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")

        # Navigate back to home screen and open Wallet app
        if not self.StartApp(app=self.p_BundleIds.Wallet):
            return False

        return result

    def DisableAirplaneMode(self) -> bool:
        '''
        Disables airplane mode and opens the Wallet app.

        @return: `True` if airplane mode is disabled and Wallet is opened; `False` otherwise.
        '''
        result = True

        if self.StartApp(app=self.p_BundleIds.Settings):

            # Handle back button inside settings
            if self.WaitForElementPresence(element=self.p_UIElements.backButton, displayed=True, time_ms=2000.00):
                result &= self.TapElement(self.p_UIElements.backButton)

            # Scroll to locate airplane mode toggle
            self.SwipeDown(repeat_count=2, back_interval_ms=200.00)

            # Check airplane mode switch presence
            if self.WaitForElementPresence(element=self.p_UIElements.airplaneModeSwitch, displayed=True, time_ms=2000.00):
                if self.GetElementText(self.p_UIElements.airplaneModeSwitch) == "1":
                    result &= self.TapElement(self.p_UIElements.airplaneModeSwitch)

                    # Verify airplane mode is disabled
                    if self.GetElementText(self.p_UIElements.airplaneModeSwitch) == "0":
                        AddComment("Airplane mode disabled.")
                        result &= True
                    else:
                        result &= False
                        AddComment("Airplane mode did not reach disabled state. Check log files for a screenshot of the device.")
                        self.LogDeviceScreenShot(f"{Prepare._tcName}_DisableAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")
            else:
                result &= False
                AddComment("Airplane switch not present on screen. Check log files for a screenshot of the device.")
                self.LogDeviceScreenShot(f"{Prepare._tcName}_DisableAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")
        else:
            result &= False
            AddComment("Settings app not present on screen. Check log files for a screenshot of the device.")
            self.LogDeviceScreenShot(f"{Prepare._tcName}_DisableAirplaneMode_{datetime.now():%Y_%m_%d_%H_%M}.png")

        # Navigate back to home screen and open Wallet app
        if not self.StartApp(app=self.p_BundleIds.Wallet):
            return False

        return result

    def PressVehicleStatusButton(self):
        raise NotImplementedError
    
class SmartDeviceAndroid(SmartDevice):
    def __init__(self, device, sp_num, **kwargs):
        '''
        Initialize an Android SmartDevice instance.
        @param device: The device object representing the SmartDevice.
        @param sp_num: The SmartDevice number or identifier.
        @param kwargs: Additional keyword arguments.
        '''
        SmartDevice.__init__(self, device, sp_num, **kwargs)
    
    # Placeholder for Android-specific functionality
