from aiogram.fsm.state import State, StatesGroup


class AnalyzeStates(StatesGroup):
    waiting_wallet = State()
    waiting_period = State()
    waiting_custom_period = State()
    analyzing = State()


class ChatStates(StatesGroup):
    chatting = State()
