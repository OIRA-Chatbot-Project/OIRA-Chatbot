from src.repository.abstract_repository import AbstractRepository

class MessageRepository(AbstractRepository):
    pass


"""
approach1: id, user_id, session_id, title, time, messages(as json)

prefer: SQL
approach2: id, user_id, session_id, message_id, time, message 
               session_id, title

"""