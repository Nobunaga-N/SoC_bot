import time
import random
from typing import List
from .tutorial_engine import TutorialEngine, TutorialStep
from ..utils.logger import get_logger

logger = get_logger(__name__)


def create_tutorial_steps(engine: TutorialEngine) -> List[TutorialStep]:
    """
    Создание списка шагов туториала для Sea of Conquest.

    Args:
        engine: Движок туториала

    Returns:
        Список шагов туториала
    """
    steps = []

    # Шаг 1: Клик по иконке профиля
    steps.append(TutorialStep(
        id="step1",
        description="Клик по иконке профиля",
        action=engine.click_on_image,
        args=("open_profile",),
        timeout=15.0
    ))

    # Шаг 2: Клик по иконке настроек
    steps.append(TutorialStep(
        id="step2",
        description="Клик по иконке настроек",
        action=engine.click_on_coordinates,
        args=(1073, 35),
        timeout=5.0
    ))

    # Шаг 3: Клик по иконке персонажей
    steps.append(TutorialStep(
        id="step3",
        description="Клик по иконке персонажей",
        action=engine.click_on_coordinates,
        args=(638, 319),
        timeout=5.0
    ))

    # Шаг 4: Клик по иконке добавления персонажей
    steps.append(TutorialStep(
        id="step4",
        description="Клик по иконке добавления персонажей",
        action=engine.click_on_coordinates,
        args=(270, 184),
        timeout=5.0
    ))

    # Шаг 5: Выбор сезона
    steps.append(TutorialStep(
        id="step5",
        description="Выбор сезона",
        action=engine.find_season_and_click,
        args=(engine.server_range[0],),  # Используем первый сервер из диапазона
        timeout=10.0
    ))

    # Шаг 6: Выбор сервера
    steps.append(TutorialStep(
        id="step6",
        description="Выбор сервера",
        action=engine.find_server_and_click,
        args=(engine.server_range[0],),  # Используем первый сервер из диапазона
        timeout=20.0
    ))

    # Шаг 7: Клик по кнопке подтверждения
    steps.append(TutorialStep(
        id="step7",
        description="Клик по кнопке подтверждения",
        action=engine.click_on_image,
        args=("confirm_new_acc",),
        timeout=10.0
    ))

    # Шаг 8: Ожидание загрузки
    steps.append(TutorialStep(
        id="step8",
        description="Ожидание загрузки",
        action=engine.wait_fixed_time,
        args=(10.0,),
        timeout=12.0
    ))

    # Шаг 9: Поиск и клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step9",
        description="Поиск и клик по кнопке пропуска",
        action=lambda: _find_and_click_skip(engine),
        timeout=20.0,
        retry_count=5
    ))

    # Шаг 10: Поиск и клик по кнопке пропуска или кнопке выстрела
    steps.append(TutorialStep(
        id="step10",
        description="Поиск и клик по кнопке пропуска или кнопке выстрела",
        action=lambda: _find_and_click_skip_or_shoot(engine),
        timeout=20.0,
        retry_count=5
    ))

    # Шаг 11: Ожидание и клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step11",
        description="Ожидание и клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=30.0
    ))

    # Шаг 12: Ожидание экрана с Hell_Genry
    steps.append(TutorialStep(
        id="step12",
        description="Ожидание экрана с Hell_Genry",
        action=engine.wait_for_image,
        args=("Hell_Genry",),
        timeout=60.0
    ))

    # Шаг 13: Клик по lite_apks
    steps.append(TutorialStep(
        id="step13",
        description="Клик по lite_apks",
        action=engine.click_on_image,
        args=("lite_apks",),
        timeout=10.0
    ))

    # Шаг 14: Сложный свайп
    steps.append(TutorialStep(
        id="step14",
        description="Сложный свайп",
        action=engine.perform_complex_swipe,
        args=([
                  (154, 351),
                  (288, 355),
                  (507, 353),
                  (627, 351)
              ],),
        timeout=10.0
    ))

    # Шаг 15: Клик по кнопке закрытия меню
    steps.append(TutorialStep(
        id="step15",
        description="Клик по кнопке закрытия меню",
        action=engine.click_on_image,
        args=("close_menu",),
        timeout=10.0
    ))

    # Шаг 16: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step16",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 17: Клик по изображению корабля
    steps.append(TutorialStep(
        id="step17",
        description="Клик по изображению корабля",
        action=engine.click_on_image,
        args=("ship",),
        timeout=10.0
    ))

    # Шаг 18: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step18",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 19: Ожидание 5 секунд
    steps.append(TutorialStep(
        id="step19",
        description="Ожидание 5 секунд",
        action=engine.wait_fixed_time,
        args=(5.0,),
        timeout=7.0
    ))

    # Шаг 20: Клик по координатам
    steps.append(TutorialStep(
        id="step20",
        description="Клик по координатам 637, 368",
        action=engine.click_on_coordinates,
        args=(637, 368),
        timeout=5.0
    ))

    # Шаг 21: Клик по координатам
    steps.append(TutorialStep(
        id="step21",
        description="Клик по координатам 637, 368",
        action=engine.click_on_coordinates,
        args=(637, 368),
        timeout=5.0
    ))

    # Шаг 22: Клик по координатам
    steps.append(TutorialStep(
        id="step22",
        description="Клик по координатам 637, 368",
        action=engine.click_on_coordinates,
        args=(637, 368),
        timeout=5.0
    ))

    # Шаг 23: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step23",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 24: Клик по координатам
    steps.append(TutorialStep(
        id="step24",
        description="Клик по координатам 342, 387",
        action=engine.click_on_coordinates,
        args=(342, 387),
        timeout=5.0
    ))

    # Шаг 25: Клик по координатам
    steps.append(TutorialStep(
        id="step25",
        description="Клик по координатам 79, 294",
        action=engine.click_on_coordinates,
        args=(79, 294),
        timeout=5.0
    ))

    # Шаг 26: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step26",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 27: Клик по координатам
    steps.append(TutorialStep(
        id="step27",
        description="Клик по координатам 739, 137",
        action=engine.click_on_coordinates,
        args=(739, 137),
        timeout=5.0
    ))

    # Шаг 28: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step28",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 29: Клик по координатам
    steps.append(TutorialStep(
        id="step29",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 30: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step30",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 31: Клик по координатам
    steps.append(TutorialStep(
        id="step31",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 32: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step32",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 33: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step33",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 34: Клик по координатам
    steps.append(TutorialStep(
        id="step34",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 35: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step35",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 36: Клик по иконке навигатора
    steps.append(TutorialStep(
        id="step36",
        description="Клик по иконке навигатора",
        action=engine.click_on_image,
        args=("navigator",),
        timeout=10.0
    ))

    # Шаг 37: Клик по координатам
    steps.append(TutorialStep(
        id="step37",
        description="Клик по координатам 699, 269",
        action=engine.click_on_coordinates,
        args=(699, 269),
        timeout=5.0
    ))

    # Шаг 38: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step38",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 39: Клик по координатам
    steps.append(TutorialStep(
        id="step39",
        description="Клик по координатам 141, 30",
        action=engine.click_on_coordinates,
        args=(141, 30),
        timeout=5.0
    ))

    # Шаг 40: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step40",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 41: Клик по координатам
    steps.append(TutorialStep(
        id="step41",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 42: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step42",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 43: Клик по координатам с задержкой
    steps.append(TutorialStep(
        id="step43",
        description="Клик по координатам 146, 286 с задержкой 2 секунды",
        action=engine.click_on_coordinates,
        args=(146, 286, 2.0),  # Добавляем задержку 2 секунды
        timeout=7.0
    ))

    # Шаг 44: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step44",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 45: Клик по координатам
    steps.append(TutorialStep(
        id="step45",
        description="Клик по координатам 228, 341",
        action=engine.click_on_coordinates,
        args=(228, 341),
        timeout=5.0
    ))

    # Шаг 46: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step46",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 47: Клик по координатам
    steps.append(TutorialStep(
        id="step47",
        description="Клик по координатам 228, 341",
        action=engine.click_on_coordinates,
        args=(228, 341),
        timeout=5.0
    ))

    # Шаг 48: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step48",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 49: Клик по иконке лица героя
    steps.append(TutorialStep(
        id="step49",
        description="Клик по иконке лица героя",
        action=engine.click_on_image,
        args=("hero_face",),
        timeout=10.0
    ))

    # Шаг 50: Клик по кнопке начала битвы
    steps.append(TutorialStep(
        id="step50",
        description="Клик по кнопке начала битвы",
        action=engine.click_on_image,
        args=("start_battle",),
        timeout=10.0
    ))

    # Шаг 51: Многократный клик до появления кнопки начала битвы
    steps.append(TutorialStep(
        id="step51",
        description="Многократный клик до появления кнопки начала битвы",
        action=lambda: _click_until_image_found(engine, 642, 324, "start_battle", 1.5),
        timeout=30.0
    ))

    # Шаг 52: Многократный клик до появления кнопки пропуска (не более 7 раз)
    steps.append(TutorialStep(
        id="step52",
        description="Многократный клик до появления кнопки пропуска",
        action=lambda: _click_until_image_found(engine, 642, 324, "skip", 1.5, 7),
        timeout=20.0
    ))

    # Шаг 53: Клик по координатам
    steps.append(TutorialStep(
        id="step53",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 54: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step54",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 55: Клик по координатам
    steps.append(TutorialStep(
        id="step55",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 56: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step56",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 57: Клик по координатам
    steps.append(TutorialStep(
        id="step57",
        description="Клик по координатам 656, 405",
        action=engine.click_on_coordinates,
        args=(656, 405),
        timeout=5.0
    ))

    # Шаг 58-60: Клик по кнопке пропуска
    for i in range(58, 61):
        steps.append(TutorialStep(
            id=f"step{i}",
            description=f"Клик по кнопке пропуска ({i - 57}/3)",
            action=engine.click_on_image,
            args=("skip",),
            timeout=10.0
        ))

    # Шаги 70-72: Клик по кнопке пропуска
    for i in range(70, 73):
        steps.append(TutorialStep(
            id=f"step{i}",
            description=f"Клик по кнопке пропуска ({i - 69}/3)",
            action=engine.click_on_image,
            args=("skip",),
            timeout=10.0
        ))

    # Шаг 73: Клик по координатам
    steps.append(TutorialStep(
        id="step73",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 74: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step74",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 75: Клик по координатам
    steps.append(TutorialStep(
        id="step75",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 76: Клик по координатам
    steps.append(TutorialStep(
        id="step76",
        description="Клик по координатам 44, 483",
        action=engine.click_on_coordinates,
        args=(44, 483),
        timeout=5.0
    ))

    # Шаг 77: Клик по координатам
    steps.append(TutorialStep(
        id="step77",
        description="Клик по координатам 128, 226",
        action=engine.click_on_coordinates,
        args=(128, 226),
        timeout=5.0
    ))

    # Шаг 78: Клик по кнопке улучшения корабля
    steps.append(TutorialStep(
        id="step78",
        description="Клик по кнопке улучшения корабля",
        action=engine.click_on_image,
        args=("upgrade_ship",),
        timeout=10.0
    ))

    # Шаг 79: Клик по координатам
    steps.append(TutorialStep(
        id="step79",
        description="Клик по координатам 144, 24",
        action=engine.click_on_coordinates,
        args=(144, 24),
        timeout=5.0
    ))

    # Шаг 80: Клик по координатам
    steps.append(TutorialStep(
        id="step80",
        description="Клик по координатам 639, 598",
        action=engine.click_on_coordinates,
        args=(639, 598),
        timeout=5.0
    ))

    # Шаг 90: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step90",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 91: Клик по координатам
    steps.append(TutorialStep(
        id="step91",
        description="Клик по координатам 1075, 91",
        action=engine.click_on_coordinates,
        args=(1075, 91),
        timeout=5.0
    ))

    # Шаг 92: Клик по координатам
    steps.append(TutorialStep(
        id="step92",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 93: Клик по координатам
    steps.append(TutorialStep(
        id="step93",
        description="Клик по координатам 41, 483",
        action=engine.click_on_coordinates,
        args=(41, 483),
        timeout=5.0
    ))

    # Шаг 94: Клик по координатам
    steps.append(TutorialStep(
        id="step94",
        description="Клик по координатам 975, 510",
        action=engine.click_on_coordinates,
        args=(975, 510),
        timeout=5.0
    ))

    # Шаг 95: Клик по координатам
    steps.append(TutorialStep(
        id="step95",
        description="Клик по координатам 746, 599",
        action=engine.click_on_coordinates,
        args=(746, 599),
        timeout=5.0
    ))

    # Шаг 96: Клик по координатам
    steps.append(TutorialStep(
        id="step96",
        description="Клик по координатам 639, 491",
        action=engine.click_on_coordinates,
        args=(639, 491),
        timeout=5.0
    ))

    # Шаг 97-98: Клик по координатам
    for i in range(97, 99):
        steps.append(TutorialStep(
            id=f"step{i}",
            description=f"Клик по координатам 146, 286 ({i - 96}/2)",
            action=engine.click_on_coordinates,
            args=(146, 286),
            timeout=5.0
        ))

    # Шаг 99: Клик по координатам
    steps.append(TutorialStep(
        id="step99",
        description="Клик по координатам 41, 483",
        action=engine.click_on_coordinates,
        args=(41, 483),
        timeout=5.0
    ))

    # Шаг 100: Клик по координатам
    steps.append(TutorialStep(
        id="step100",
        description="Клик по координатам 692, 504",
        action=engine.click_on_coordinates,
        args=(692, 504),
        timeout=5.0
    ))

    # Шаг 101: Клик по координатам
    steps.append(TutorialStep(
        id="step101",
        description="Клик по координатам 691, 584",
        action=engine.click_on_coordinates,
        args=(691, 584),
        timeout=5.0
    ))

    # Шаг 102: Клик по координатам
    steps.append(TutorialStep(
        id="step102",
        description="Клик по координатам 665, 516",
        action=engine.click_on_coordinates,
        args=(665, 516),
        timeout=5.0
    ))

    # Шаг 103-104: Клик по координатам
    for i in range(103, 105):
        steps.append(TutorialStep(
            id=f"step{i}",
            description=f"Клик по координатам 146, 286 ({i - 102}/2)",
            action=engine.click_on_coordinates,
            args=(146, 286),
            timeout=5.0
        ))

    # Шаг 105: Клик по иконке навигатора
    steps.append(TutorialStep(
        id="step105",
        description="Клик по иконке навигатора",
        action=engine.click_on_image,
        args=("navigator",),
        timeout=10.0
    ))

    # Шаг 106: Клик по координатам
    steps.append(TutorialStep(
        id="step106",
        description="Клик по координатам 692, 282",
        action=engine.click_on_coordinates,
        args=(692, 282),
        timeout=5.0
    ))

    # Шаг 107: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step107",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 108: Клик по координатам
    steps.append(TutorialStep(
        id="step108",
        description="Клик по координатам 648, 210",
        action=engine.click_on_coordinates,
        args=(648, 210),
        timeout=5.0
    ))

    # Шаг 109-111: Клик по кнопке пропуска
    for i in range(109, 112):
        steps.append(TutorialStep(
            id=f"step{i}",
            description=f"Клик по кнопке пропуска ({i - 108}/3)",
            action=engine.click_on_image,
            args=("skip",),
            timeout=10.0
        ))

    # Шаг 112: Клик по координатам
    steps.append(TutorialStep(
        id="step112",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 113-116: Клик по кнопке пропуска
    for i in range(113, 117):
        steps.append(TutorialStep(
            id=f"step{i}",
            description=f"Клик по кнопке пропуска ({i - 112}/4)",
            action=engine.click_on_image,
            args=("skip",),
            timeout=10.0
        ))

    # Шаг 117: Ожидание и клик по координатам
    steps.append(TutorialStep(
        id="step117",
        description="Ожидание 7 секунд и клик по координатам 967, 620",
        action=lambda: _wait_and_click(engine, 967, 620, 7.0),
        timeout=15.0
    ))

    # Шаг 118: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step118",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 119: Клик по координатам
    steps.append(TutorialStep(
        id="step119",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 120: Клик по кнопке открытия нового локального здания
    steps.append(TutorialStep(
        id="step120",
        description="Клик по кнопке открытия нового локального здания",
        action=engine.click_on_image,
        args=("open_new_local_building",),
        timeout=10.0
    ))

    # Шаг 121: Клик по кнопке пропуска
    steps.append(TutorialStep(
        id="step121",
        description="Клик по кнопке пропуска",
        action=engine.click_on_image,
        args=("skip",),
        timeout=10.0
    ))

    # Шаг 122: Клик по координатам
    steps.append(TutorialStep(
        id="step122",
        description="Клик по координатам 146, 286",
        action=engine.click_on_coordinates,
        args=(146, 286),
        timeout=5.0
    ))

    # Шаг 123: Закрытие игры
    steps.append(TutorialStep(
        id="step123",
        description="Закрытие игры",
        action=lambda: _close_game(engine),
        timeout=15.0
    ))

    # Шаг 124: Запуск игры снова
    steps.append(TutorialStep(
        id="step124",
        description="Запуск игры снова",
        action=lambda: _start_game(engine),
        timeout=20.0
    ))

    # Шаг 125: Ожидание 10 секунд
    steps.append(TutorialStep(
        id="step125",
        description="Ожидание 10 секунд",
        action=engine.wait_fixed_time,
        args=(10.0,),
        timeout=12.0
    ))

    # Шаг 126: Нажатие ESC до появления иконки профиля
    steps.append(TutorialStep(
        id="step126",
        description="Нажатие ESC до появления иконки профиля",
        action=engine.press_esc_until_image,
        args=("open_profile",),
        kwargs={"interval": 10.0, "max_attempts": 10},
        timeout=120.0
    ))

    return steps


# Вспомогательные функции для выполнения сложных шагов

def _find_and_click_skip(engine: TutorialEngine) -> bool:
    """
    Клик по случайным координатам в центре и поиск кнопки пропуска.

    Args:
        engine: Движок туториала

    Returns:
        True если кнопка найдена и нажата, иначе False
    """
    # Клик по случайным координатам в центре экрана
    center_x = 640  # Середина по горизонтали (предполагается экран 1280x720)
    center_y = 360  # Середина по вертикали

    # Добавляем немного случайности
    rand_x = center_x + random.randint(-50, 50)
    rand_y = center_y + random.randint(-50, 50)

    engine.adb.tap(rand_x, rand_y)

    # Пытаемся найти и кликнуть по кнопке пропуска
    max_attempts = 3
    for attempt in range(max_attempts):
        if engine.click_on_image("skip", timeout=4.0):
            return True

        # Если не нашли, снова кликаем по случайным координатам
        rand_x = center_x + random.randint(-50, 50)
        rand_y = center_y + random.randint(-50, 50)
        engine.adb.tap(rand_x, rand_y)

    return False


def _find_and_click_skip_or_shoot(engine: TutorialEngine) -> bool:
    """
    Поиск и клик по кнопке пропуска или кнопке выстрела.

    Args:
        engine: Движок туториала

    Returns:
        True если кнопка найдена и нажата, иначе False
    """
    max_attempts = 5
    for attempt in range(max_attempts):
        # Получаем скриншот
        screenshot = engine.adb.get_screenshot()

        # Сначала ищем кнопку выстрела
        shoot_match = engine.image_processor.find_template(screenshot, "shoot")
        if shoot_match:
            # Если нашли кнопку выстрела, кликаем по ней
            x, y = engine.image_processor.center_of_template(shoot_match)
            engine.adb.tap(x, y)
            logger.info("Найдена и нажата кнопка выстрела")
            return True

        # Если не нашли кнопку выстрела, ищем кнопку пропуска
        skip_match = engine.image_processor.find_template(screenshot, "skip")
        if skip_match:
            # Если нашли кнопку пропуска, кликаем по ней
            x, y = engine.image_processor.center_of_template(skip_match)
            engine.adb.tap(x, y)
            logger.info("Найдена и нажата кнопка пропуска")

            # После клика по кнопке пропуска снова начинаем поиск
            # кнопки пропуска или выстрела
            time.sleep(1.0)
            continue

        # Если не нашли ни одну из кнопок, ждем немного и пробуем снова
        time.sleep(1.0)

    logger.warning("Не удалось найти кнопку пропуска или выстрела")
    return False


def _close_game(engine: TutorialEngine) -> bool:
    """
    Закрытие игры.

    Args:
        engine: Движок туториала

    Returns:
        True если игра успешно закрыта, иначе False
    """
    engine.adb.execute_command("shell am force-stop com.seaofconquest.global")
    time.sleep(2.0)  # Даем время на закрытие

    # Проверяем, что игра действительно закрыта
    result = engine.adb.execute_command("shell pidof com.seaofconquest.global")
    return result.strip() == ""


def _start_game(engine: TutorialEngine) -> bool:
    """
    Запуск игры.

    Args:
        engine: Движок туториала

    Returns:
        True если игра успешно запущена, иначе False
    """
    engine.adb.execute_command(
        "shell am start -n com.seaofconquest.global/com.kingsgroup.mo.KGUnityPlayerActivity"
    )
    time.sleep(5.0)  # Даем время на запуск

    # Проверяем, что игра действительно запущена
    result = engine.adb.execute_command("shell pidof com.seaofconquest.global")
    return result.strip() != ""


def _click_until_image_found(engine: TutorialEngine, x: int, y: int, image_name: str,
                             interval: float = 1.5, max_clicks: int = None) -> bool:
    """
    Кликает по указанным координатам с интервалом, пока не найдет указанное изображение.

    Args:
        engine: Движок туториала
        x: Координата x
        y: Координата y
        image_name: Имя изображения, которое нужно найти
        interval: Интервал между кликами в секундах
        max_clicks: Максимальное количество кликов (если не указано, то без ограничений)

    Returns:
        True если изображение найдено, иначе False
    """
    click_count = 0

    while True:
        # Получаем скриншот
        screenshot = engine.adb.get_screenshot()

        # Проверяем, есть ли искомое изображение
        template_match = engine.image_processor.find_template(screenshot, image_name)

        if template_match:
            # Если нашли, кликаем по нему
            x_img, y_img = engine.image_processor.center_of_template(template_match)
            engine.adb.tap(x_img, y_img)
            logger.info(f"Найдено изображение {image_name}, клик по координатам ({x_img}, {y_img})")
            return True

        # Если не нашли, и достигли максимального количества кликов, выходим
        if max_clicks is not None and click_count >= max_clicks:
            logger.warning(f"Достигнуто максимальное количество кликов ({max_clicks}), "
                           f"изображение {image_name} не найдено")
            return False

        # Кликаем по указанным координатам
        engine.adb.tap(x, y)
        click_count += 1
        logger.debug(f"Клик #{click_count} по координатам ({x}, {y})")

        # Ждем указанный интервал
        time.sleep(interval)


def _wait_and_click(engine: TutorialEngine, x: int, y: int, wait_time: float) -> bool:
    """
    Ожидание указанного времени и клик по координатам.

    Args:
        engine: Движок туториала
        x: Координата x
        y: Координата y
        wait_time: Время ожидания в секундах

    Returns:
        True всегда
    """
    time.sleep(wait_time)
    engine.adb.tap(x, y)
    return True