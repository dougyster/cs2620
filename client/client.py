import socket
import struct
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import json

from client_wire_protocol import ClientWireProtocol
from client_json_protocol import ClientJsonProtocol
from client_serialization_interface import ClientSerializationInterface
import os

class ClientApp:
    def __init__(self, serialization_interface: ClientSerializationInterface):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = os.getenv('CHAT_APP_HOST', '0.0.0.0')  # Default to 0.0.0.0
        port = int(os.getenv('CHAT_APP_PORT', '8081'))  # Default to 8081
        self.client_socket.connect((host, port))
        self.username = ""
        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.serialization_interface = serialization_interface
        self.is_json = isinstance(serialization_interface, ClientJsonProtocol)
        self.login_screen()
        self.user_list = []
        self.last_log_off = None
        self.view_count = 5
        
    def read_exact(self, n):
        data = b''
        while len(data) < n:
            packet = self.client_socket.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def login_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame with padding
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True)
        
        # Title
        title = tk.Label(main_frame, text="Chat Client", font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 20))
        
        # Username section
        tk.Label(main_frame, text="Username").pack()
        self.username_entry = tk.Entry(main_frame)
        self.username_entry.pack()
        self.username_error = tk.Label(main_frame, text="", fg='red', font=('Arial', 8))
        self.username_error.pack()
        
        # Password section
        tk.Label(main_frame, text="Password").pack()
        self.password_entry = tk.Entry(main_frame, show="*")
        self.password_entry.pack()
        self.password_error = tk.Label(main_frame, text="", fg='red', font=('Arial', 8))
        self.password_error.pack()
        
        # Requirements info
        requirements = (
            "Username requirements:\n"
            "• Only letters and numbers\n"
            "• No spaces\n"
            "• 3-20 characters\n\n"
            "Password requirements:\n"
            "• At least 8 characters\n"
            "• At least one number\n"
            "• At least one uppercase letter\n"
            "• No spaces"
        )
        tk.Label(main_frame, text=requirements, justify=tk.LEFT, 
                font=('Arial', 8), fg='gray').pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Login", command=self.login).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Register", command=self.register).pack(side=tk.LEFT, padx=5)

    def validate_username(self, username):
        """Validate username according to requirements"""
        import re
        if not 3 <= len(username) <= 20:
            return False, "Username must be 3-20 characters long"
        if not username.isalnum():
            return False, "Username can only contain letters and numbers"
        if ' ' in username:
            return False, "Username cannot contain spaces"
        return True, ""

    def validate_password(self, password):
        """Validate password according to requirements"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if ' ' in password:
            return False, "Password cannot contain spaces"
        return True, ""

    def chat_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Configure the main window
        self.root.configure(bg='#36393f')
        self.root.geometry("1000x600")
        
        # Create main container
        main_container = tk.Frame(self.root, bg='#36393f')
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create sidebar for contacts
        sidebar = tk.Frame(main_container, width=200, bg='#2f3136')
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # Sidebar header
        tk.Label(sidebar, text="Conversations", bg='#2f3136', fg='white', font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Add search frame only if we have users
        print(f"User list before rendering bar: {self.user_list}")
        search_frame = ttk.Frame(sidebar)
        search_frame.pack(fill='x', padx=5, pady=5)
        
        # Create StringVar to track changes
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.filter_users)
        
        # Create combobox with the StringVar
        self.user_search = ttk.Combobox(search_frame, 
                                       values=self.user_list,
                                       textvariable=self.search_var)
        self.user_search.pack(fill='x')
        self.user_search.bind('<<ComboboxSelected>>', self.on_user_selected)
        
        # Style the combobox to match theme
        style = ttk.Style()
        style.configure('TCombobox', 
                       fieldbackground='#40444b',
                       background='#2f3136',
                       foreground='white')
        
        # Contacts list frame with scrollbar
        contacts_frame = tk.Frame(sidebar, bg='#2f3136')
        contacts_frame.pack(fill=tk.BOTH, expand=True)
        
        self.contacts_list = tk.Listbox(contacts_frame, bg='#2f3136', fg='white', 
                                       selectmode=tk.SINGLE, relief=tk.FLAT,
                                       font=('Arial', 10))
        self.contacts_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.contacts_list.bind('<<ListboxSelect>>', self.on_contact_select)
        
        # Add delete account button at the bottom of sidebar
        delete_account_btn = tk.Button(
            sidebar,
            text="Delete Account",
            command=self.delete_account,
            bg='#ED4245',  # Discord's danger red
            fg='black',
            relief=tk.FLAT,
            font=('Arial', 10),
            padx=10,
            pady=5,
            activebackground='#c03537',  # Darker red for hover
            activeforeground='white'
        )
        delete_account_btn.pack(side=tk.BOTTOM, pady=10)
        
        # Add stats frame above delete button
        stats_frame = tk.Frame(sidebar, bg='#2f3136')
        stats_frame.pack(side=tk.BOTTOM, fill='x', padx=5, pady=5)
        
        # Last log-off time label
        self.log_off_label = tk.Label(
            stats_frame, 
            text="Last log-off: Never",
            bg='#2f3136',
            fg='white',
            font=('Arial', 8),
            wraplength=180
        )
        self.log_off_label.pack(fill='x', pady=2)
        
        # View count frame
        view_count_frame = tk.Frame(stats_frame, bg='#2f3136')
        view_count_frame.pack(fill='x')
        
        # View count label and entry
        self.view_count_label = tk.Label(
            view_count_frame,
            text=f"View Count: {self.view_count}",
            bg='#2f3136',
            fg='white',
            font=('Arial', 8)
        )
        self.view_count_label.pack(side=tk.LEFT, pady=2)
        
        # Update view count button
        self.view_count_entry = tk.Entry(view_count_frame, width=5)
        self.view_count_entry.pack(side=tk.LEFT, padx=5)
        self.view_count_entry.insert(0, str(self.view_count))
        
        update_btn = tk.Button(
            view_count_frame,
            text="Update",
            command=self.update_view_count,
            bg='#5865f2',
            fg='black',
            font=('Arial', 8),
            relief=tk.FLAT
        )
        update_btn.pack(side=tk.RIGHT)
        
        # Chat area container
        chat_container = tk.Frame(main_container, bg='#36393f')
        chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Chat header
        self.chat_header = tk.Label(chat_container, text="Select a conversation", 
                                   bg='#36393f', fg='white', font=('Arial', 12, 'bold'))
        self.chat_header.pack(fill=tk.X, pady=10)
        
        # Chat messages area with scrollbar
        self.chat_area = tk.Text(chat_container, bg='#36393f', fg='white', 
                                wrap=tk.WORD, state='disabled')
        scrollbar = tk.Scrollbar(chat_container, command=self.chat_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10)
        self.chat_area.configure(yscrollcommand=scrollbar.set)
        
        # Message input area
        input_frame = tk.Frame(chat_container, bg='#36393f')
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.message_entry = tk.Entry(input_frame, bg='#40444b', fg='white', 
                                     relief=tk.FLAT, font=('Arial', 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        
        send_button = tk.Button(input_frame, text="Send", command=self.send_message,
                               bg='#000080', fg='black', relief=tk.FLAT,
                               font=('Arial', 10), padx=15, pady=5,
                               activebackground='#4752c4', activeforeground='white')
        send_button.pack(side=tk.RIGHT)
        
        # Start receiving messages
        self.messages_by_user = {}  # Store messages by user
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def on_contact_select(self, event):
        selection = self.contacts_list.curselection()
        if selection:
            contact = self.contacts_list.get(selection[0])
            self.current_contact = contact
            self.chat_header.config(text=f"Chat with {contact}")
            self.display_conversation(contact)

    def display_conversation(self, contact):
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        
        if contact in self.messages_by_user:
            messages = self.messages_by_user[contact]
            
            # Split messages into before and after last_log_off
            messages_before = []
            messages_after = []
            
            for msg in messages:
                # Extract timestamp from message format "[2024-03-14 12:34:56] [sender -> receiver]: content"
                msg_time_str = msg[1:20]
                try:
                    msg_time = datetime.strptime(msg_time_str, '%Y-%m-%d %H:%M:%S')
                    
                    if self.last_log_off is None or msg_time <= self.last_log_off:
                        messages_before.append(msg)
                    else:
                        messages_after.append(msg)
                except ValueError:
                    # If there's any issue parsing the timestamp, treat as an old message
                    messages_before.append(msg)
            
            # Display all messages before last_log_off
            for msg in messages_before:
                self.display_message(msg)
            
            # If there are messages after last_log_off
            if messages_after:
                # Add a visual separator
                separator = tk.Frame(self.chat_area, height=2, bg='#5865f2')
                self.chat_area.window_create(tk.END, window=separator, stretch=True)
                self.chat_area.insert(tk.END, '\nNew messages since last login:\n\n')
                
                # Display first batch of messages based on view_count
                self.current_message_index = 0
                self.remaining_messages = messages_after
                self.display_next_batch()
        
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def display_next_batch(self):
        """Display next batch of messages based on view_count"""
        if not hasattr(self, 'remaining_messages'):
            return
            
        end_index = min(self.current_message_index + self.view_count, len(self.remaining_messages))
        current_batch = self.remaining_messages[self.current_message_index:end_index]
        
        # Display current batch
        for msg in current_batch:
            self.display_message(msg)
        
        # Update current index
        self.current_message_index = end_index
        
        # If there are more messages, show the "View More" button
        if self.current_message_index < len(self.remaining_messages):
            self.show_view_more_button()

    def display_message(self, msg):
        """Display a single message with delete button"""
        msg_frame = tk.Frame(self.chat_area, bg='#36393f')
        self.chat_area.window_create(tk.END, window=msg_frame)
        
        # Add message text
        msg_label = tk.Label(msg_frame, text=msg, bg='#36393f', fg='white',
                            wraplength=500, justify=tk.LEFT)
        msg_label.pack(side=tk.LEFT, pady=2)
        
        # Add delete button
        delete_btn = tk.Button(
            msg_frame, 
            text="×", 
            bg='#36393f', 
            fg='black',
            font=('Arial', 8),
            relief=tk.FLAT,
            command=lambda m=msg: self.handle_delete_message(m, self.current_contact)
        )
        delete_btn.pack(side=tk.RIGHT, padx=5)
        
        self.chat_area.insert(tk.END, '\n')

    def show_view_more_button(self):
        """Create and display the View More button"""
        remaining_count = len(self.remaining_messages) - self.current_message_index
        
        button_frame = tk.Frame(self.chat_area, bg='#36393f')
        self.chat_area.window_create(tk.END, window=button_frame)
        
        view_more_btn = tk.Button(
            button_frame,
            text=f"View More ({remaining_count} messages remaining)",
            command=self.display_next_batch,
            bg='#5865f2',
            fg='black',
            relief=tk.FLAT,
            font=('Arial', 10),
            padx=10,
            pady=5,
            activebackground='#4752c4',
            activeforeground='white'
        )
        view_more_btn.pack(pady=10)
        
        # Remove the old button before displaying new messages
        def display_and_remove():
            button_frame.destroy()
            self.display_next_batch()
        
        view_more_btn.configure(command=display_and_remove)
        self.chat_area.insert(tk.END, '\n')

    def update_contacts_list(self):
        self.contacts_list.delete(0, tk.END)
        for contact in sorted(self.messages_by_user.keys()):
            self.contacts_list.insert(tk.END, contact)

    def serialize_message(self, msg_type, lst):
        return self.serialization_interface.serialize_message(msg_type, lst)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # Reset error messages
        self.username_error.config(text="")
        self.password_error.config(text="")
        
        # Validate inputs
        username_valid, username_error = self.validate_username(username)
        password_valid, password_error = self.validate_password(password)
        
        if not username_valid:
            self.username_error.config(text=username_error)
            return
        if not password_valid:
            self.password_error.config(text=password_error)
            return
        
        data = self.serialize_message('L', [username, password])
        print(f"Sending login: {len(data)} bytes")  
        # Proceed with login
        self.client_socket.sendall(data)
        
        # Get response
        if self.is_json:
            response = self.read_json_response()
            if response[0]['type'] == 'S':
                self.username = username
                messagebox.showinfo("Success", response[0]['payload'])
                self.request_user_list()
                self.chat_screen()
            else:
                messagebox.showerror("Error", response[0]['payload'])
        else:
            header = self.read_exact(5)
            if not header:
                messagebox.showerror("Error", "Connection closed")
                return
                
            msg_type, payload_len = struct.unpack('!BI', header)
            payload = self.read_exact(payload_len)
            
            if chr(msg_type) == 'S':
                self.username = username
                messagebox.showinfo("Success", payload.decode())
                self.request_user_list()
                self.chat_screen()
            else:
                messagebox.showerror("Error", payload.decode())

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # Reset error messages
        self.username_error.config(text="")
        self.password_error.config(text="")
        
        # Validate inputs
        username_valid, username_error = self.validate_username(username)
        password_valid, password_error = self.validate_password(password)
        
        if not username_valid:
            self.username_error.config(text=username_error)
            return
        if not password_valid:
            self.password_error.config(text=password_error)
            return
        
        # Proceed with registration
        self.client_socket.sendall(self.serialize_message('R', [username, password]))
        
        # Get response
        if self.is_json:
            response = self.read_json_response()
            if response[0]['type'] == 'S':
                messagebox.showinfo("Success", response[0]['payload'])
            else:
                messagebox.showerror("Error", response[0]['payload'])
        else:
            header = self.read_exact(5)
            if not header:
                messagebox.showerror("Error", "Connection closed")
                return
                
            msg_type, payload_len = struct.unpack('!BI', header)
            payload = self.read_exact(payload_len)
            
            if chr(msg_type) == 'S':
                messagebox.showinfo("Success", payload.decode())
            else:
                messagebox.showerror("Error", payload.decode())

    def read_json_response(self) -> list:
        """Read complete JSON responses from the socket"""
        buffer = b''
        messages = []
        
        while True:
            chunk = self.client_socket.recv(4096)
            if not chunk:
                return None
            
            buffer += chunk
            try:
                # Try to find complete JSON messages
                decoded = buffer.decode('utf-8')
                depth = 0
                start = 0
                
                for i, char in enumerate(decoded):
                    if char == '{':
                        if depth == 0:
                            start = i
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            # Found a complete JSON message
                            message = decoded[start:i+1]
                            messages.append(json.loads(message))
                            # Move start past this message
                            start = i + 1
                
                # Keep any incomplete message in buffer
                if start < len(decoded):
                    buffer = decoded[start:].encode('utf-8')
                else:
                    buffer = b''
                
                # If we have any messages, return them
                if messages:
                    return messages
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If we can't parse yet, keep reading
                continue

    def send_message(self):
        if not hasattr(self, 'current_contact'):
            messagebox.showerror("Error", "Please select a contact first")
            return
        
        message = self.message_entry.get()
        if not message:
            return
        
        recipient = self.current_contact
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = self.serialize_message('M', [self.username, recipient, message])
        print(f"Sending message: {len(data)} bytes")
        self.client_socket.sendall(data)

        # Add message to chat area immediately
        self.chat_area.config(state='normal')
        formatted_message = f"[{timestamp}] [{self.username} -> {recipient}]: {message}"
        self.chat_area.insert(tk.END, formatted_message + '\n')
        self.chat_area.see(tk.END)  # Scroll to bottom
        self.chat_area.config(state='disabled')

        # Store message in history
        if recipient not in self.messages_by_user:
            self.messages_by_user[recipient] = []
        self.messages_by_user[recipient].append(formatted_message)
        
        self.message_entry.delete(0, tk.END)

    def receive_messages(self):
        """Handle incoming messages from server"""
        while True:
            try:
                
                if self.is_json:
                    responses = self.read_json_response()
                    for response in responses:
                        msg_type = response['type']
                        payload = response['payload']
                        print(f"Received JSON response - Type: {msg_type}")
                        print(f"Payload: {payload}")
                        if not self.receive_message_helper(msg_type, payload):
                            return
                else:
                    header = self.read_exact(5)
                    if not header:
                        break
                    b_msg_type, payload_len = struct.unpack('!BI', header)
                    msg_type = chr(b_msg_type)
                    payload = self.read_exact(payload_len)
                    if not self.receive_message_helper(msg_type, payload):
                        return

            except Exception as e:
                print(f"Receive error: {e}")
                break
    
    def receive_message_helper(self, msg_type, payload) -> bool:
        if msg_type == 'M':
            sender, recipient, msg_content = self.serialization_interface.deserialize_message(payload)
            self.chat_area.config(state='normal')
            self.chat_area.insert(tk.END, f"[{sender}]: {msg_content}\n")
            self.chat_area.config(state='disabled')

            self.animate_message()

        elif msg_type == 'B':  # Bulk message delivery (stored messages)
            self.handle_bulk_messages(payload)
        
        elif msg_type == 'U':  # User list
            print(f"User list: {payload}")
            self.handle_user_list(payload)

        elif msg_type == 'V':  # User stats
            time_str, view_count = self.serialization_interface.deserialize_user_stats(payload)
            self.view_count = view_count
            if time_str == "None":
                self.last_log_off = None
            else:
                self.last_log_off = datetime.fromisoformat(time_str)
            
            # Update the UI
            self.update_stats_display()

        elif msg_type == 'S':  # For delete confirmation
            if self.serialization_interface.deserialize_success(payload) == "Message deleted":
                messagebox.showinfo("Success", "Message deleted successfully")
            elif self.serialization_interface.deserialize_success(payload) == "User deleted successfully":
                messagebox.showinfo("Success", "Account deleted successfully")
                self.root.after(0, self.login_screen)  # Return to login screen
                return False # Exit the receive loop
            elif self.serialization_interface.deserialize_success(payload) == "View count updated":
                messagebox.showinfo("Success", "View count updated successfully")
        
        return True
    
    def animate_message(self):
        self.chat_area.config(state='normal')
        end = self.chat_area.index(tk.END)
        
        # Get system background color
        bg_color = self.root.cget('bg')
        is_dark = self._is_dark_theme(bg_color)
        
        # Configure colors based on theme
        if is_dark:
            flash_colors = ["#404000", "#303000", None]  # Dark yellow to system background
        else:
            flash_colors = ["#ffff00", "#ffff88", None]  # Bright yellow to system background
        
        # Create animation tags
        self.chat_area.tag_config("flash", background=flash_colors[0])
        self.chat_area.tag_add("flash", f"{end}-2l", end)
        
        # Animate background color
        self.flash_animation(0, end, flash_colors)

    def flash_animation(self, count, position, colors):
        if count < len(colors):
            color = colors[count]
            if color is None:  # Reset to system background
                self.chat_area.tag_delete("flash")
            else:
                self.chat_area.tag_config("flash", background=color)
            self.root.after(150, lambda: self.flash_animation(count+1, position, colors))

    def _is_dark_theme(self, color):
        """Determine if the system theme is dark based on background color."""
        try:
            # Convert color name to RGB
            rgb = self.root.winfo_rgb(color)
            # Convert 16-bit RGB values to 8-bit
            r, g, b = rgb[0]//256, rgb[1]//256, rgb[2]//256
            # Calculate perceived brightness
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        except:
            return False  # Default to light theme if color parsing fails

    def handle_bulk_messages(self, payload):
        """Handle bulk message delivery (stored messages)."""
        try:
            # Update UI on main thread
            self.root.after(0, self.update_chat_with_messages, self.serialization_interface.deserialize_bulk_messages(payload, self.username, self.messages_by_user))
            
        except Exception as e:
            print(f"Error handling bulk messages: {e}")

    def update_chat_with_messages(self, messages):
        self.update_contacts_list()
        # If a contact is selected, update the chat area
        selection = self.contacts_list.curselection()
        if selection:
            self.display_conversation(self.contacts_list.get(selection[0]))

    def request_user_list(self):
        """Request the list of all users from the server"""
        self.client_socket.sendall(self.serialization_interface.serialize_user_list())
    
    def handle_user_list(self, payload: bytes) -> list:
        """
        Deserialize the user list from the server response
        Returns a list of usernames
        """
        self.user_list = self.serialization_interface.deserialize_user_list(payload)
        
        # Update the combobox with new user list
        if hasattr(self, 'user_search'):
            self.user_search['values'] = self.user_list
        return

    def create_search_frame(self):
        """Create a simple search frame for users"""
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill='x', padx=5, pady=5)
        
        # Create combobox that will show filtered results
        self.user_search = ttk.Combobox(search_frame, values=self.user_list)
        self.user_search.pack(fill='x')
        
        # Bind selection event
        self.user_search.bind('<<ComboboxSelected>>', self.on_user_selected)
        
    def on_user_selected(self, event):
        """Handle user selection from combobox"""
        selected_user = self.user_search.get()
        if selected_user and selected_user != self.username:  # Don't start chat with yourself
            # Add user to contacts if not already there
            if selected_user not in self.messages_by_user:
                self.messages_by_user[selected_user] = []
                self.update_contacts_list()
            # Select the user in contacts list
            idx = list(self.messages_by_user.keys()).index(selected_user)
            self.contacts_list.selection_clear(0, tk.END)
            self.contacts_list.selection_set(idx)
            self.on_contact_select(None)  # Update chat area

    def filter_users(self, *args):
        """Filter users based on search text"""
        search_text = self.search_var.get().lower()
        filtered_users = [
            user for user in self.user_list 
            if search_text in user.lower() and user != self.username
        ]
        self.user_search['values'] = filtered_users
        
        # Keep the dropdown open while typing
        if filtered_users:
            self.user_search.event_generate('<Down>')

    def delete_message(self, message_content, timestamp, sender, receiver):
        """Serialize and send a delete message request"""
        self.client_socket.sendall(self.serialize_message('D', [message_content, timestamp, sender, receiver]))

    def handle_delete_message(self, message, contact):
        """Handle the deletion of a message"""
        if messagebox.askyesno("Delete Message", "Are you sure you want to delete this message?"):
            try:
                timestamp = message[1:20]  # Extract timestamp
                content_start = message.index(']:') + 3
                content = message[content_start:].strip()
                
                # Send delete request
                self.delete_message(content, timestamp, self.username, contact)
                
                # Remove from local storage
                if contact in self.messages_by_user:
                    # Remove the message
                    self.messages_by_user[contact].remove(message)
                    
                    # Refresh display
                    self.chat_area.config(state='normal')
                    self.chat_area.delete(1.0, tk.END)
                    # Don't reset current_message_index here
                    self.display_conversation(contact)
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete message: {e}")

    def delete_account(self):
        """Send a request to delete the current user's account"""
        if messagebox.askyesno("Delete Account", 
                              "Are you sure you want to delete your account? This cannot be undone."):
            self.client_socket.sendall(self.serialize_message('U', [self.username]))

    def update_view_count(self):
        try:
            new_count = int(self.view_count_entry.get())
            if new_count < 0:
                messagebox.showerror("Error", "View count must be positive")
                return
            self.client_socket.sendall(self.serialize_message('W', [self.username, new_count]))
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def update_stats_display(self):
        """Update the stats labels with current values"""
        if hasattr(self, 'log_off_label'):
            log_off_text = f"Last log-off: {self.last_log_off or 'Never'}"
            self.log_off_label.config(text=log_off_text)
        
        if hasattr(self, 'view_count_label'):
            self.view_count_label.config(text=f"View Count: {self.view_count}")

if __name__ == "__main__":
    wire_protocol = ClientWireProtocol()
    json_protocol = ClientJsonProtocol()
    
    # Choose which protocol to use 
    app = ClientApp(json_protocol) # change protocol here
    app.root.mainloop()