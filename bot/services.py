import csv
import codecs
import datetime
from re import escape
from os import remove


def already_signed_up_for_tour(user_id: int, db) -> bool:
    tours_participants = db["tour_participants"]
    signed_up = tours_participants.find_one({"user_id": user_id})
    if signed_up:
        return signed_up["tour"]
    return False


def tour_no_free_places(tour) -> bool:
    if tour["free_places"] > 0:
        return False
    return True


def free_places_validation(db, tour_name: str):
    tours = db["tours"]

    for t in tours.find({}):
        if t["name"] == tour_name:
            tour = t

    if tour_no_free_places(tour):
        return False

    return tour


def decrement_free_places(tour_name, db) -> None:
    tours = db["tours"]
    tours.update_one(
        {"name": tour_name},
        {"$inc": {"free_places": -1}},
    )


def add_tour_participant(db, user_data: dict) -> None:
    tour_participants = db["tour_participants"]
    tour_participants.insert_one(
        {
            "user_id": user_data["user_id"],
            "tour": user_data["tour_name"],
            "user_name": user_data["tour_user_name"],
            "user_phone": user_data["tour_user_phone"],
        }
    )
    if "tour_user_passport" in user_data:
        tour_participants.update_one(
            {"user_id": user_data["user_id"]},
            {"$set": {"user_passport": user_data["tour_user_passport"]}},
        )


def get_all_tours(db, only_free: bool = True):
    tours = db["tours"]
    if only_free:
        tours = tours.find({"free_places": {"$gt": 0}})
    else:
        tours = tours.find({})
    return list(tours)


def get_residence_info(db, user_name: str, info: str) -> str:
    participants = db["participants"]
    # TODO: find several and return list
    result = participants.find_one({"name": {"$regex": "^" + escape(user_name)}})[info]
    return result


def get_transfer_in_info(db, user_name: str):
    collection = db["transfers_in"]
    result = collection.find({"full_name": {"$regex": "^" + escape(user_name)}})
    result = list(result)
    return result


def get_transfer_out_info(db, user_name: str):
    collection = db["transfers_out"]
    result = collection.find({"full_name": {"$regex": "^" + escape(user_name)}})
    result = list(result)
    return result


async def tours_to_csv(db, update):
    collection = db["tour_participants"]
    data = list(collection.find())

    field_names = set()
    for document in data:
        field_names.update(document.keys())

    temp_csv_file = "data.csv"
    with codecs.open(temp_csv_file, "w", encoding="utf-8") as csvfile:
        csv_writer = csv.DictWriter(csvfile, fieldnames=field_names)
        csv_writer.writeheader()
        csv_writer.writerows(data)

    with open(temp_csv_file, "rb") as file:
        await update.message.reply_document(
            caption="Файл готов ✅",
            filename="participants.csv",
            document=file,
        )

    remove(temp_csv_file)


def add_user_to_db(db, user_id: int):
    users = db["users"]

    if users.find_one({"id": user_id}):
        return
    users.insert_one({"id": user_id, "datetime": str(datetime.datetime.now())})


def get_notification(db):
    from datetime import datetime

    current_date = datetime.now()
    current_hour = current_date.hour

    collection = db["notifications"]
    text = collection.find_one(
        {"date": current_date.strftime("%Y-%m-%d"), "hour": current_hour}
    )["text"]
    return text


def get_tour_users(db, tour_name: str):
    collection = db["tour_participants"]
    users = collection.find({"tour": tour_name})
    return users
