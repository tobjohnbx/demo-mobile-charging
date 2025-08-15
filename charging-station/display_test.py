#!/usr/bin/env python3
"""
Display Test File for ChargingDisplay - Happy Path Demo

This test file shows a continuous happy path workflow of the charging station display.
It cycles through all the main screens automatically with delays so you can observe
the complete user experience flow.

Usage:
    python display_test.py

The test will continuously cycle through the happy path workflow.
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
    Test class for demonstrating the happy path charging workflow
    """

    def __init__(self):
        self.display = None
        self.test_data = self._prepare_test_data()

    def _prepare_test_data(self):
        """Prepare realistic test data for display methods"""
        now = datetime.now()
        return {
            'tag_id': 123456789012,
            'start_time': now,
            'charging_duration': 25.5,  # 25.5 minutes
            'cost': 2.55,
        }

    def show_happy_path_workflow(self):
        """Show the complete happy path charging workflow"""
        print("🔄 Starting Happy Path Charging Workflow Demo")
        print("Press Ctrl+C to exit at any time")
        print("-" * 50)

        cycle_count = 1

        try:
            while True:
                print(f"\n🔄 Workflow Cycle #{cycle_count}")

                # 1. Welcome Screen
                print("1️⃣  Welcome Screen (5s)")
                self.display.show_welcome_message()
                time.sleep(5)

                # 3. Card Detected
                print("3️⃣  Card Detected (3s)")
                self.display.show_card_detected(self.test_data['tag_id'])
                time.sleep(3)

                # 2. Pricing Information
                print("2️⃣  Pricing Information - Different Quantity Types (6s)")
                # Example with day rate per minute
                self.display.show_pricing_info("08:00", "22:00", 0.1000, "MINUTE")
                time.sleep(2)

                # Example with pricing per second
                print("2️⃣b Per Second Pricing (2s)")
                self.display.show_pricing_info("06:00", "18:00", 0.0017, "SECOND")
                time.sleep(2)

                # Example with night rate (FREE)
                print("2️⃣c Night Rate - FREE (2s)")
                self.display.show_pricing_info("22:00", "08:00", 0.0000, "MINUTE")
                time.sleep(2)

                # 4. Charging Started
                print("4️⃣  Charging Started (4s)")
                start_time = datetime.now()
                self.display.show_charging_started(self.test_data['tag_id'], start_time)
                time.sleep(4)

                # 5. Active Charging (simulate 15 seconds of charging with blinking)
                print("5️⃣  Active Charging - Blinking Animation (15s)")
                for second in range(15):
                    duration = (second + 1) * 1.7  # Simulate increasing duration
                    self.display.show_charging_active(start_time, duration)
                    time.sleep(1)

                # 6. Charging Stopped (without cost first)
                print("6️⃣  Charging Stopped - Processing (3s)")
                self.display.show_charging_stopped(self.test_data['charging_duration'])
                time.sleep(3)

                # 7. Charging Stopped (with cost)
                print("7️⃣  Charging Stopped - With Cost (4s)")
                self.display.show_charging_stopped(
                    self.test_data['charging_duration'],
                    self.test_data['cost']
                )
                time.sleep(4)

                # 8. API Success
                print("8️⃣  Billing Success (3s)")
                self.display.show_api_success("Billing processed")
                time.sleep(3)

                # 9. Back to Welcome (brief transition)
                print("9️⃣  Back to Welcome (2s)")
                self.display.show_welcome_message()
                time.sleep(2)

                cycle_count += 1
                print(f"✅ Completed cycle #{cycle_count - 1}")
                print("🔄 Starting next cycle in 3 seconds...")
                time.sleep(3)

        except KeyboardInterrupt:
            print("\n\n⚠️  Demo stopped by user")
            print("🧹 Returning to welcome screen...")
            self.display.show_welcome_message()

    def run_demo(self):
        """Initialize display and run the happy path demo"""
        print("🚀 ChargingDisplay Happy Path Demo")
        print("=" * 50)
        print("This demo shows the complete charging workflow automatically.")
        print("Each screen will be displayed for a few seconds.")
        print("The demo will loop continuously until you press Ctrl+C.")
        print("=" * 50)

        try:
            print("\n🔧 Initializing display...")
            self.display = ChargingDisplay()
            time.sleep(2)
            print("✅ Display initialized successfully")

            # Show current pricing info
            current_time = datetime.now().time()
            if current_time >= datetime.strptime("22:00:00", "%H:%M:%S").time() or \
               current_time < datetime.strptime("08:00:00", "%H:%M:%S").time():
                pricing_info = "FREE (Night Rate: 22:00-08:00)"
            else:
                pricing_info = "€0.10/min (Day Rate: 08:00-22:00)"

            print(f"💰 Current pricing: {pricing_info}")
            print(f"🏷️  Test tag ID: {self.test_data['tag_id']}")
            print(f"⏱️  Simulated session: {self.test_data['charging_duration']} minutes")
            print(f"💵 Simulated cost: €{self.test_data['cost']:.2f}")

            print("\n🎬 Starting demo in 3 seconds...")
            time.sleep(3)

            self.show_happy_path_workflow()

        except Exception as e:
            print(f"\n❌ Fatal error during demo: {e}")
            traceback.print_exc()
        finally:
            # Clean up - return to welcome screen
            try:
                if self.display:
                    print("\n🧹 Final cleanup - showing welcome screen...")
                    self.display.show_welcome_message()
            except:
                pass


def main():
    """Main function to run the display demo"""
    try:
        tester = DisplayTester()
        tester.run_demo()
    except Exception as e:
        print(f"Failed to start demo: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
