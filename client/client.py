import socket
import struct
import threading
import tkinter as tk
from tkinter import messagebox

class ClientApp:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('10.250.133.226', 8081))
        self.username = ""
        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.login_screen()
        
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
            
        self.chat_area = tk.Text(self.root, state='disabled')
        self.chat_area.pack()
        
        self.recipient_entry = tk.Entry(self.root, width=15)
        self.recipient_entry.pack(side='left')
        
        self.message_entry = tk.Entry(self.root, width=40)
        self.message_entry.pack(side='left')
        
        tk.Button(self.root, text="Send", command=self.send_message).pack()
        threading.Thread(target=self.receive_messages, daemon=True).start()

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
        recipient = self.recipient_entry.get()
        msg_content = self.message_entry.get()
        
        payload = (
            struct.pack('!H', len(self.username)) + self.username.encode() +
            struct.pack('!H', len(recipient)) + recipient.encode() +
            struct.pack('!I', len(msg_content)) + msg_content.encode()
        )
        self.client_socket.sendall(self.serialize_message('M', payload))

        # Display the sent message in the chat window
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"[You -> {recipient}]: {msg_content}\n")
        self.chat_area.config(state='disabled')

        # Clear the message entry field for new input
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

                        # Display the message in the chat window
                        self.chat_area.config(state='normal')
                        self.chat_area.insert(tk.END, f"[{readable_timestamp}] [Stored][{sender} -> {receiver}]: {content}\n")
                        self.chat_area.config(state='disabled')


                    
            except Exception as e:
                print(f"Receive error: {e}")
                break
    
    def animate_message(self):
        self.chat_area.config(state='normal')
        end = self.chat_area.index(tk.END)
        
        # Create animation tags
        self.chat_area.tag_config("flash", background="#ffff00")
        self.chat_area.tag_add("flash", f"{end}-2l", end)
        
        # Animate background color
        self.flash_animation(0, end)

    def flash_animation(self, count, position):
        colors = ["#ffff00", "#ffff88", "#ffffff"]
        self.chat_area.tag_config("flash", background=colors[count])
        if count < 2:
            self.root.after(150, lambda: self.flash_animation(count+1, position))

if __name__ == "__main__":
    app = ClientApp()
    app.root.mainloop()

import socket
import struct
import threading
import tkinter as tk
from tkinter import messagebox

class ClientApp:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('10.250.133.226', 8081))
        self.username = ""
        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.login_screen()
        
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
            
        self.chat_area = tk.Text(self.root, state='disabled')
        self.chat_area.pack()
        
        self.recipient_entry = tk.Entry(self.root, width=15)
        self.recipient_entry.pack(side='left')
        
        self.message_entry = tk.Entry(self.root, width=40)
        self.message_entry.pack(side='left')
        
        tk.Button(self.root, text="Send", command=self.send_message).pack()
        threading.Thread(target=self.receive_messages, daemon=True).start()

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
        recipient = self.recipient_entry.get()
        msg_content = self.message_entry.get()
        
        payload = (
            struct.pack('!H', len(self.username)) + self.username.encode() +
            struct.pack('!H', len(recipient)) + recipient.encode() +
            struct.pack('!I', len(msg_content)) + msg_content.encode()
        )
        self.client_socket.sendall(self.serialize_message('M', payload))

        # Display the sent message in the chat window
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"[You -> {recipient}]: {msg_content}\n")
        self.chat_area.config(state='disabled')

        # Clear the message entry field for new input
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

                        # Display the message in the chat window
                        self.chat_area.config(state='normal')
                        self.chat_area.insert(tk.END, f"[{readable_timestamp}] [Stored][{sender} -> {receiver}]: {content}\n")
                        self.chat_area.config(state='disabled')

                    
            except Exception as e:
                print(f"Receive error: {e}")
                break
    
    # def animate_message(self):
    #     self.chat_area.config(state='normal')
    #     end = self.chat_area.index(tk.END)
        
    #     # Create animation tags
    #     self.chat_area.tag_config("flash", background="#ffff00")
    #     self.chat_area.tag_add("flash", f"{end}-2l", end)
        
    #     # Animate background color
    #     self.flash_animation(0, end)

    # def flash_animation(self, count, position):
    #     colors = ["#ffff00", "#ffff88", "#ffffff"]
    #     self.chat_area.tag_config("flash", background=colors[count])
    #     if count < 2:
    #         self.root.after(150, lambda: self.flash_animation(count+1, position))

if __name__ == "__main__":
    app = ClientApp()
    app.root.mainloop()