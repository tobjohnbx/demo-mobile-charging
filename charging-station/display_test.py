#!/usr/bin/env python3
"""
Display Test File for ChargingDisplay

This test file allows you to manually test all display methods on your physical screen.
Run this file to see each display method in action with realistic test data.

Usage:
    python display_test.py

The test will cycle through all display methods with pauses so you can observe each output.
Press Ctrl+C at any time to exit the test.
"""

import sys
import time
from datetime import datetime, timedelta
import traceback

# Import the display module
try:
    from display import ChargingDisplay
except ImportError as e:
    print(f"ERROR: Could not import ChargingDisplay: {e}")
    print("Make sure display.py is in the same directory as this test file.")
    sys.exit(1)


class DisplayTester:
    """
    Test class for manually testing ChargingDisplay methods
    """

    def __init__(self):
        self.display = None
        self.test_data = self._prepare_test_data()

    def _prepare_test_data(self):
        """Prepare realistic test data for display methods"""
        now = datetime.now()
        return {
            'tag_id': 123456789012,
            'short_tag_id': 12345,
            'start_time': now - timedelta(minutes=15),
            'current_time': now,
            'duration_short': 2.5,
            'duration_medium': 15.3,
            'duration_long': 125.7,
            'cost_low': 2.45,
            'cost_high': 18.95,
            'success_messages': [
                "Billing sent",
                "Usage recorded",
                "Payment processed",
                "Session complete"
            ],
            'error_messages': [
                "Network timeout",
                "Auth failed",
                "API unavailable",
                "Connection lost"
            ],
            'status_messages': [
                "Initializing...",
                "Connecting to API",
                "Updating firmware",
                "Self-test complete"
            ]
        }

    def _wait_for_input(self, message="Press Enter to continue to next test (or 'q' to quit)..."):
        """Wait for user input before proceeding"""
        try:
            user_input = input(f"\n{message}")
            if user_input.lower() in ['q', 'quit', 'exit']:
                return False
            return True
        except KeyboardInterrupt:
            return False

    def _test_method(self, method_name, method_func, description):
        """Test a single display method with error handling"""
        print(f"\n{'='*60}")
        print(f"Testing: {method_name}")
        print(f"Description: {description}")
        print(f"{'='*60}")

        try:
            method_func()
            print(f"✅ {method_name} executed successfully")
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
            print(f"Traceback: {traceback.format_exc()}")

        return self._wait_for_input()

    def test_initialization(self):
        """Test display initialization"""
        def init_test():
            print("Initializing ChargingDisplay...")
            self.display = ChargingDisplay()
            time.sleep(2)

        return self._test_method(
            "Display Initialization",
            init_test,
            "Initialize the display and show welcome message"
        )

    def test_clear_display(self):
        """Test clearing the display"""
        def clear_test():
            print("Clearing display...")
            self.display.clear_display()
            time.sleep(2)

        return self._test_method(
            "clear_display()",
            clear_test,
            "Clear all content from the display"
        )

    def test_welcome_message(self):
        """Test welcome message display"""
        def welcome_test():
            print("Showing welcome message...")
            self.display.show_welcome_message()
            time.sleep(3)

        return self._test_method(
            "show_welcome_message()",
            welcome_test,
            "Show the initial welcome screen with EV Charging text"
        )

    def test_card_detected(self):
        """Test card detection displays"""
        def card_test():
            for i, tag_id in enumerate([
                self.test_data['tag_id'],
                self.test_data['short_tag_id'],
                999888777666
            ]):
                print(f"Showing card detected {i+1}/3 (Tag ID: {tag_id})...")
                self.display.show_card_detected(tag_id)
                time.sleep(2)

        return self._test_method(
            "show_card_detected()",
            card_test,
            "Show card detection with different tag IDs"
        )

    def test_charging_started(self):
        """Test charging started display"""
        def start_test():
            tag_id = self.test_data['tag_id']
            start_time = self.test_data['start_time']
            print(f"Showing charging started (Tag: {tag_id}, Time: {start_time.strftime('%H:%M')})...")
            self.display.show_charging_started(tag_id, start_time)
            time.sleep(3)

        return self._test_method(
            "show_charging_started()",
            start_test,
            "Show charging session start screen"
        )

    def test_charging_active(self):
        """Test active charging display with blinking effect"""
        def active_test():
            start_time = self.test_data['start_time']
            durations = [
                self.test_data['duration_short'],
                self.test_data['duration_medium'],
                self.test_data['duration_long']
            ]

            for i, duration in enumerate(durations):
                print(f"Showing active charging {i+1}/3 (Duration: {duration:.1f} min)...")
                # Show for 6 seconds to see blinking effect
                for _ in range(6):
                    self.display.show_charging_active(start_time, duration)
                    time.sleep(1)

        return self._test_method(
            "show_charging_active()",
            active_test,
            "Show active charging with blinking animation and different durations"
        )

    def test_charging_stopped(self):
        """Test charging stopped displays"""
        def stop_test():
            # Test without cost
            print("Showing charging stopped (without cost)...")
            self.display.show_charging_stopped(self.test_data['duration_medium'])
            time.sleep(3)

            # Test with cost
            print("Showing charging stopped (with cost)...")
            self.display.show_charging_stopped(
                self.test_data['duration_medium'],
                self.test_data['cost_low']
            )
            time.sleep(3)

        return self._test_method(
            "show_charging_stopped()",
            stop_test,
            "Show charging stopped with and without cost information"
        )

    def test_api_success(self):
        """Test API success displays"""
        def success_test():
            # Test default message
            print("Showing API success (default message)...")
            self.display.show_api_success()
            time.sleep(2)

            # Test custom messages
            for i, message in enumerate(self.test_data['success_messages']):
                print(f"Showing API success {i+1}/{len(self.test_data['success_messages'])} ('{message}')...")
                self.display.show_api_success(message)
                time.sleep(2)

        return self._test_method(
            "show_api_success()",
            success_test,
            "Show API success with default and custom messages"
        )

    def test_api_error(self):
        """Test API error displays"""
        def error_test():
            # Test default message
            print("Showing API error (default message)...")
            self.display.show_api_error()
            time.sleep(2)

            # Test custom messages
            for i, message in enumerate(self.test_data['error_messages']):
                print(f"Showing API error {i+1}/{len(self.test_data['error_messages'])} ('{message}')...")
                self.display.show_api_error(message)
                time.sleep(2)

        return self._test_method(
            "show_api_error()",
            error_test,
            "Show API errors with default and custom messages"
        )

    def test_system_status(self):
        """Test system status displays"""
        def status_test():
            for i, status in enumerate(self.test_data['status_messages']):
                print(f"Showing system status {i+1}/{len(self.test_data['status_messages'])} ('{status}')...")
                self.display.show_system_status(status)
                time.sleep(2)

        return self._test_method(
            "show_system_status()",
            status_test,
            "Show various system status messages"
        )

    def test_temporary_message(self):
        """Test temporary message display"""
        def temp_test():
            messages = [
                ("Short message", 2),
                ("Medium length message here", 3),
                ("Very long message that might wrap", 4)
            ]

            for i, (message, duration) in enumerate(messages):
                print(f"Showing temporary message {i+1}/{len(messages)} ('{message}' for {duration}s)...")
                # Note: This will block for the duration
                self.display.show_temporary_message(message, duration)

        return self._test_method(
            "show_temporary_message()",
            temp_test,
            "Show temporary messages with different durations"
        )

    def test_pricing_info(self):
        """Test pricing information display"""
        def pricing_test():
            print("Showing current pricing information...")
            self.display.show_pricing_info()
            time.sleep(4)

            print("Note: Pricing shown depends on current time:")
            current_time = datetime.now().time()
            if current_time >= datetime.strptime("22:00:00", "%H:%M:%S").time() or \
               current_time < datetime.strptime("08:00:00", "%H:%M:%S").time():
                print("  - Current time shows: FREE (22:00-08:00)")
            else:
                print("  - Current time shows: €0.10/min (08:00-22:00)")

        return self._test_method(
            "show_pricing_info()",
            pricing_test,
            "Show time-based pricing information screen"
        )

    def test_complete_workflow(self):
        """Test a complete charging workflow simulation"""
        def workflow_test():
            print("Starting complete workflow simulation...")

            # Welcome
            print("1. Welcome screen...")
            self.display.show_welcome_message()
            time.sleep(2)

            # Card detected
            print("2. Card detected...")
            self.display.show_card_detected(self.test_data['tag_id'])
            time.sleep(2)

            # Charging started
            print("3. Charging started...")
            start_time = datetime.now()
            self.display.show_charging_started(self.test_data['tag_id'], start_time)
            time.sleep(3)

            # Active charging (simulate 10 seconds)
            print("4. Active charging (10 seconds)...")
            for second in range(10):
                duration = second / 60.0  # Convert to minutes
                self.display.show_charging_active(start_time, duration)
                time.sleep(1)

            # Charging stopped
            print("5. Charging stopped...")
            self.display.show_charging_stopped(10/60.0, 0.85)  # 10 seconds, small cost
            time.sleep(3)

            # API success
            print("6. Billing processed...")
            self.display.show_api_success("Billing processed")
            time.sleep(2)

            # Back to welcome
            print("7. Back to welcome...")
            self.display.show_welcome_message()
            time.sleep(2)

        return self._test_method(
            "Complete Workflow",
            workflow_test,
            "Simulate a complete charging session workflow"
        )

    def run_all_tests(self):
        """Run all display tests"""
        print("🔧 ChargingDisplay Test Suite")
        print("="*60)
        print("This test will cycle through all display methods.")
        print("Each test will show the output on your physical display.")
        print("Press Ctrl+C at any time to exit.")
        print("="*60)

        if not self._wait_for_input("Press Enter to start testing..."):
            return

        # List of all tests
        tests = [
            self.test_initialization,
            self.test_clear_display,
            self.test_welcome_message,
            self.test_card_detected,
            self.test_charging_started,
            self.test_charging_active,
            self.test_charging_stopped,
            self.test_api_success,
            self.test_api_error,
            self.test_system_status,
            self.test_temporary_message,
            self.test_pricing_info,
            self.test_complete_workflow
        ]

        try:
            for i, test in enumerate(tests):
                print(f"\n📋 Running test {i+1}/{len(tests)}")
                if not test():
                    print("\n👋 Testing stopped by user")
                    break
            else:
                print("\n🎉 All tests completed successfully!")
                print("The display should now show the welcome message.")

        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")
        except Exception as e:
            print(f"\n❌ Fatal error during testing: {e}")
            traceback.print_exc()
        finally:
            # Clean up - return to welcome screen
            try:
                if self.display:
                    print("\n🧹 Cleaning up - returning to welcome screen...")
                    self.display.show_welcome_message()
            except:
                pass


def main():
    """Main function to run the display tests"""
    print("🚀 Starting ChargingDisplay Test Suite...")

    try:
        tester = DisplayTester()
        tester.run_all_tests()
    except Exception as e:
        print(f"Failed to start testing: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
