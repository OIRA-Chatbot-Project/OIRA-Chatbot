import abc
import object

class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def _add(self, obj: object) -> None:
        """Subclasses must implement this method"""
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self,  obj: object) -> object:
        """Subclasses must implement this method"""
        raise NotImplementedError

    @abc.abstractmethod
    def __update(self,  obj: object) -> None:
        """Subclasses must implement this method"""
        raise NotImplementedError