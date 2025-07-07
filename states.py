# states.py
from aiogram.fsm.state import State, StatesGroup

class MeditationStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_rating = State()
    waiting_for_marathon_title = State()
    waiting_for_marathon_description = State()
    waiting_for_marathon_dates = State()
    waiting_for_marathon_goal = State()

class DialogueStates(StatesGroup):
    in_dialogue = State()
    waiting_for_manual_entry = State()
    confirming_manual_entry = State()
    adding_comment = State()
    adding_rating = State()
