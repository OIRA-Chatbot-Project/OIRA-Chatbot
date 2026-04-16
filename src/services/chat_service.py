from repository.message_repository import MessageRepository
from src.repository.knowledge_repository import KnowledgeRepository

class ChatService:
    def __init__(self):
        self.knowledge_repo = KnowledgeRepository()
        self.message_repo = MessageRepository()
    
    async def chat(self):
        pass
    