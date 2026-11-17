"""
Voice Assistant for Shop Credit Tracker
Listens continuously for voice commands and automates tasks.
"""

import threading
import time
import requests
import json
from datetime import datetime

class VoiceAssistant:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.listening = False
        self.recognition = None
        self.session = requests.Session()
        
    def setup_recognition(self):
        """Setup speech recognition"""
        try:
            import speech_recognition as sr
            self.recognition = sr.Recognizer()
            self.microphone = sr.Microphone()
            print("✅ Voice recognition initialized")
            return True
        except ImportError:
            print("❌ SpeechRecognition not installed. Install with: pip install SpeechRecognition pyaudio")
            return False
        except Exception as e:
            print(f"❌ Error setting up recognition: {e}")
            return False
    
    def listen_for_command(self):
        """Listen for a single voice command"""
        if not self.recognition:
            return None
            
        try:
            with self.microphone as source:
                self.recognition.adjust_for_ambient_noise(source, duration=0.5)
                print("🎤 Listening...")
                audio = self.recognition.listen(source, timeout=5, phrase_time_limit=10)
                
            text = self.recognition.recognize_google(audio).lower()
            print(f"🗣️ Heard: '{text}'")
            return text
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def parse_command(self, text):
        """Parse voice command and return action"""
        text = text.lower()
        
        # Command patterns
        if any(word in text for word in ['add credit', 'gave credit', 'credit']):
            return self.parse_credit_command(text)
        elif any(word in text for word in ['add payment', 'got payment', 'payment', 'paid']):
            return self.parse_payment_command(text)
        elif any(word in text for word in ['show dashboard', 'dashboard', 'home']):
            return {'action': 'navigate', 'page': '/'}
        elif any(word in text for word in ['show customers', 'customers']):
            return {'action': 'navigate', 'page': '/customers'}
        elif any(word in text for word in ['add customer', 'new customer']):
            return {'action': 'navigate', 'page': '/add_customer'}
        elif any(word in text for word in ['stop', 'exit', 'quit']):
            return {'action': 'stop'}
        else:
            print(f"❓ Unknown command: {text}")
            return None
    
    def parse_credit_command(self, text):
        """Parse credit command: 'add credit for [name] [amount]'"""
        import re
        
        # Extract amount
        amount_match = re.search(r'(\d+)', text)
        amount = int(amount_match.group(1)) if amount_match else None
        
        # Extract customer name (everything between 'for' and amount, or after 'credit')
        name_match = re.search(r'for\s+(\w+)', text)
        if name_match:
            name = name_match.group(1)
        else:
            # Try to find name before amount
            words = text.split()
            name = None
            for i, word in enumerate(words):
                if word.isdigit():
                    name = words[i-1] if i > 0 else None
                    break
        
        if name and amount:
            return {
                'action': 'add_transaction',
                'type': 'credit',
                'customer_name': name,
                'amount': amount
            }
        return None
    
    def parse_payment_command(self, text):
        """Parse payment command: 'add payment for [name] [amount]'"""
        import re
        
        # Extract amount
        amount_match = re.search(r'(\d+)', text)
        amount = int(amount_match.group(1)) if amount_match else None
        
        # Extract customer name
        name_match = re.search(r'for\s+(\w+)', text)
        if name_match:
            name = name_match.group(1)
        else:
            words = text.split()
            name = None
            for i, word in enumerate(words):
                if word.isdigit():
                    name = words[i-1] if i > 0 else None
                    break
        
        if name and amount:
            return {
                'action': 'add_transaction',
                'type': 'payment',
                'customer_name': name,
                'amount': amount
            }
        return None
    
    def execute_command(self, command):
        """Execute parsed command"""
        if not command:
            return
        
        action = command.get('action')
        
        if action == 'add_transaction':
            self.add_transaction(
                command['customer_name'],
                command['type'],
                command['amount']
            )
        elif action == 'navigate':
            print(f"🌐 Navigate to: {command['page']}")
            # This would need to be handled by the frontend
        elif action == 'stop':
            self.listening = False
            print("🛑 Stopping voice assistant")
    
    def add_transaction(self, customer_name, trans_type, amount):
        """Add transaction via API"""
        try:
            # First, get customer ID from name
            customers = self.session.get(f"{self.base_url}/api/customers").json()
            customer_id = None
            
            for customer in customers:
                if customer['name'].lower() == customer_name.lower():
                    customer_id = customer['id']
                    break
            
            if not customer_id:
                print(f"❌ Customer '{customer_name}' not found")
                return
            
            # Add transaction
            data = {
                'customer_id': customer_id,
                'type': trans_type,
                'amount': amount,
                'note': f'Voice command at {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            }
            
            response = self.session.post(f"{self.base_url}/api/transaction", json=data)
            
            if response.status_code == 200:
                print(f"✅ Added {trans_type} of ₹{amount} for {customer_name}")
            else:
                print(f"❌ Failed to add transaction: {response.text}")
                
        except Exception as e:
            print(f"❌ Error adding transaction: {e}")
    
    def start_listening(self):
        """Start continuous listening loop"""
        if not self.setup_recognition():
            return
        
        self.listening = True
        print("🎙️ Voice Assistant started. Say commands like:")
        print("   - 'Add credit for Ravi 500'")
        print("   - 'Add payment for Suresh 1000'")
        print("   - 'Stop' to exit")
        
        while self.listening:
            command_text = self.listen_for_command()
            
            if command_text:
                command = self.parse_command(command_text)
                if command:
                    self.execute_command(command)
            
            time.sleep(0.5)  # Small delay between listens


def main():
    """Run the voice assistant"""
    assistant = VoiceAssistant()
    assistant.start_listening()


if __name__ == "__main__":
    main()
