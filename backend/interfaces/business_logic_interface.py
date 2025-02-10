from abc import ABC, abstractmethod

class BusinessLogicInterface(ABC):
    @abstractmethod
    def create_user(self, user_name, user_email, user_password) -> bool:
        """Create a new user with the provided details."""
        pass

    @abstractmethod
    def get_user(self, user_email) -> dict:
        """Retrieve a user by their email."""
        pass

    @abstractmethod
    def send_message(self, sender, receiver, message) -> bool:
        """Send a message from the sender to the receiver."""
        pass

    @abstractmethod
    def get_messages(self, sender, receiver) -> list:
        """Retrieve messages exchanged between the sender and receiver."""
        pass

    @abstractmethod
    def update_view_count(self, view_count, user_email) -> bool:
        """Update the view count for a specified user."""
        pass
