from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Callable, Concatenate, ParamSpec, TypeVar
from contextvars import ContextVar

from flask_socketio import SocketIO

if TYPE_CHECKING:
    from ntracer.ntracer_state import NtracerState

T = TypeVar("T")
P = ParamSpec("P")

# Context variable to track current user
current_user_id: ContextVar[str] = ContextVar('current_user_id', default='anonymous')

def __get_injector():
    # Store per-user state instead of singleton
    user_states: dict[str, NtracerState] = {}
    socketio_instance: SocketIO | None = None

    def set_socketio(s: SocketIO):
        nonlocal socketio_instance
        if socketio_instance is not None:
            raise Exception("SocketIO already set")
        print("Setting socketio")
        socketio_instance = s

    def inject_state(f: Callable[Concatenate[NtracerState, P], T]) -> Callable[P, T]:
        """Inject user-specific state - NO user_id injection"""
        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal user_states
            from ntracer.ntracer_state import NtracerState

            user_id = current_user_id.get()
            
            if user_id not in user_states:
                print(f"Creating new state for user: {user_id}")
                user_states[user_id] = NtracerState()

            # Only inject state (user-specific), not user_id
            return f(user_states[user_id], *args, **kwargs)
        return wrapper

    def inject_state_and_socket(
        f: Callable[Concatenate[NtracerState, SocketIO, P], T]
    ) -> Callable[P, T]:
        """Inject user-specific state and socketio - NO user_id injection"""
        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            from ntracer.ntracer_state import NtracerState

            nonlocal user_states, socketio_instance
            
            user_id = current_user_id.get()
            
            if user_id not in user_states:
                print(f"Creating new state for user: {user_id}")
                user_states[user_id] = NtracerState()

            if socketio_instance is None:
                raise Exception("SocketIO not set")

            return f(user_states[user_id], socketio_instance, *args, **kwargs)
        return wrapper

    def get_current_user():
        """Get current user_id if needed in specific functions"""
        return current_user_id.get()

    return inject_state, inject_state_and_socket, set_socketio, get_current_user

# Singleton instances
inject_state, inject_state_and_socketio, set_socketio, get_current_user = __get_injector()

@inject_state
def get_state(state: NtracerState) -> NtracerState:
    """Same signature as before - just returns user-specific state now"""
    return state
