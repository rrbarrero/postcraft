"""Base agent class using LangGraph for orchestration."""

from abc import ABC, abstractmethod
from typing import Any


class AgentState(dict):
    """Base state for all agents."""

    pass


class BaseAgent[T](ABC):
    """Abstract base class for all agents using LangGraph.

    Subclasses must define their own state schema and nodes.
    """

    def __init__(self, name: str) -> None:
        """Initialize the agent.

        Args:
            name: The agent's identifier.
        """
        self.name = name
        self._graph: Any = None

    @abstractmethod
    def create_graph(self) -> Any:  # type: ignore[return]
        """Create and compile the LangGraph state machine.

        Returns:
            A compiled LangGraph StateGraph.
        """
        ...

    def run(self, initial_state: Any) -> Any:
        """Run the agent with the given initial state.

        Args:
            initial_state: Initial state for the agent.

        Returns:
            Final state after agent execution.
        """
        if self._graph is None:
            self._graph = self.create_graph()

        return self._graph.invoke(initial_state)
