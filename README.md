# Mobile Automation Library Overview

This repository contains a Python-based mobile automation framework built on **Selenium** and **Appium**, structured in two main layers:

## 1. `Mobile.py` - Wrapper Layer
- Serves as the **wrapper** for interacting with mobile devices.
- Built on top of **Selenium WebDriver** and **Appium**.
- Provides reusable methods to perform actions like tap, swipe, input text, and more.

## 2. `SmartDevice.py` - Test Steps Layer
- Represents the **higher-level test layer**.
- Uses the `Mobile.py` wrapper to implement **test scenarios and steps**.
- Makes writing and maintaining automated tests faster and more structured.

This layered approach separates the **device control logic** from the **test steps**, improving maintainability, reusability, and clarity across projects.
