from repository.message_repository import MessageRepository
from src.repository.knowledge_repository import KnowledgeRepository


class ChatService:
    def __init__(self):
        self.knowledge_repo = KnowledgeRepository()
        self.message_repo = MessageRepository()
        



    async def chat(self):
        pass


    def get_messages(self, chat_id: str):
        return self.message_repo._get(chat_id)
    
    def edit_message(self, message_id: str, new_content: str):
        message = self.message_repo._get(message_id)
        if message:
            message.content = new_content
            self.message_repo.__update(message)