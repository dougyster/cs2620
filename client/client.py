import socket
import struct
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

class ClientApp:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('10.250.133.226', 8081))
        self.username = ""
        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.login_screen()
        self.user_list = []
        
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
            
        tk.Label(self.root, text="Username").pack()
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
        
        tk.Label(self.root, text="Password").pack()
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack()
        
        tk.Button(self.root, text="Login", command=self.login).pack()
        tk.Button(self.root, text="Register", command=self.register).pack()

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
        self.search_var.trace('w', self.filter_users)
        
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
                               bg='#5865f2', fg='white', relief=tk.FLAT,
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
            for msg in self.messages_by_user[contact]:
                self.chat_area.insert(tk.END, msg + '\n')
        self.chat_area.config(state='disabled')

    def update_contacts_list(self):
        self.contacts_list.delete(0, tk.END)
        for contact in sorted(self.messages_by_user.keys()):
            self.contacts_list.insert(tk.END, contact)

    def serialize_message(self, msg_type, payload):
        return struct.pack('!BI', ord(msg_type), len(payload)) + payload

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        payload = (
            struct.pack('!H', len(username)) + username.encode() +
            struct.pack('!H', len(password)) + password.encode()
        )
        self.client_socket.sendall(self.serialize_message('L', payload))
        
        # Get response
        header = self.read_exact(5)
        if not header:
            messagebox.showerror("Error", "Connection closed")
            return
            
        msg_type, payload_len = struct.unpack('!BI', header)
        payload = self.read_exact(payload_len)
        print(f"payload: {payload}")
        
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
        
        payload = (
            struct.pack('!H', len(username)) + username.encode() +
            struct.pack('!H', len(password)) + password.encode()
        )
        self.client_socket.sendall(self.serialize_message('R', payload))
        
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

    def send_message(self):
        if not hasattr(self, 'current_contact'):
            messagebox.showerror("Error", "Please select a contact first")
            return
        
        message = self.message_entry.get()
        if not message:
            return
        
        recipient = self.current_contact
        payload = (
            struct.pack('!H', len(self.username)) + self.username.encode() +
            struct.pack('!H', len(recipient)) + recipient.encode() +
            struct.pack('!I', len(message)) + message.encode()
        )
        
        self.client_socket.sendall(self.serialize_message('M', payload))

        # Add message to chat area immediately
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"[{self.username}]: {message}\n")
        self.chat_area.see(tk.END)  # Scroll to bottom
        self.chat_area.config(state='disabled')

        # Store message in history
        if recipient not in self.messages_by_user:
            self.messages_by_user[recipient] = []
        self.messages_by_user[recipient].append(f"[{self.username}]: {message}")
        
        self.message_entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                header = self.read_exact(5)
                if not header:
                    break
                msg_type, payload_len = struct.unpack('!BI', header)
                payload = self.read_exact(payload_len)
                
                if chr(msg_type) == 'M':
                    offset = 0
                    sender_len = struct.unpack_from('!H', payload, offset)[0]
                    offset += 2
                    sender = payload[offset:offset+sender_len].decode()
                    offset += sender_len
                    recipient_len = struct.unpack_from('!H', payload, offset)[0]
                    offset += 2
                    recipient = payload[offset:offset+recipient_len].decode()
                    offset += recipient_len
                    msg_len = struct.unpack_from('!I', payload, offset)[0]
                    offset += 4
                    msg_content = payload[offset:offset+msg_len].decode()
                    
                    self.chat_area.config(state='normal')
                    self.chat_area.insert(tk.END, f"[{sender}]: {msg_content}\n")
                    self.chat_area.config(state='disabled')

                    self.animate_message()

                elif chr(msg_type) == 'B':  # Bulk message delivery (stored messages)
                    self.handle_bulk_messages(payload)
                
                elif chr(msg_type) == 'U':  # User list
                    print(f"User list: {payload}")
                    self.handle_user_list(payload)

            except Exception as e:
                print(f"Receive error: {e}")
                break
    
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
            messages_to_process = []
            offset = 0
            while offset < len(payload):
                # Read the length of the packed message
                msg_len = struct.unpack_from('!I', payload, offset)[0]
                offset += 4

                # Extract the packed message
                msg_data = payload[offset:offset + msg_len]
                offset += msg_len

                # Deserialize individual fields from the packed message
                sender_len = struct.unpack_from('!H', msg_data, 0)[0]
                sender = msg_data[2:2 + sender_len].decode()

                receiver_len_offset = 2 + sender_len
                receiver_len = struct.unpack_from('!H', msg_data, receiver_len_offset)[0]
                receiver = msg_data[receiver_len_offset + 2:receiver_len_offset + 2 + receiver_len].decode()

                content_offset = receiver_len_offset + 2 + receiver_len
                content_len = struct.unpack_from('!I', msg_data, content_offset)[0]
                content = msg_data[content_offset + 4:content_offset + 4 + content_len].decode()

                timestamp_offset = content_offset + 4 + content_len
                timestamp = struct.unpack_from('!I', msg_data, timestamp_offset)[0]

                # Convert timestamp to a human-readable format
                from datetime import datetime
                readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

                # Store message by user
                other_user = sender if sender != self.username else receiver
                if other_user not in self.messages_by_user:
                    self.messages_by_user[other_user] = []
                
                msg_text = f"[{readable_timestamp}] [{sender} -> {receiver}]: {content}"
                self.messages_by_user[other_user].append(msg_text)
                messages_to_process.append((other_user, msg_text))
            
            # Update UI on main thread
            self.root.after(0, self.update_chat_with_messages, messages_to_process)
            
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
        msg_type = 'G'
        payload = b''  # Empty payload for this request
        header = struct.pack('!BI', ord(msg_type), len(payload))
        self.client_socket.sendall(header + payload)
    
    def handle_user_list(self, payload: bytes) -> list:
        """
        Deserialize the user list from the server response
        Returns a list of usernames
        """
        self.user_list = []  # Reset the list first
        offset = 0
        while offset < len(payload):
            username_len = struct.unpack('!H', payload[offset:offset + 2])[0]
            offset += 2
            username = payload[offset:offset + username_len].decode('utf-8')
            offset += username_len
            self.user_list.append(username)
        print(f"User list: {self.user_list}")
        
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

if __name__ == "__main__":
    app = ClientApp()
    app.root.mainloop()