METRICS = {
    # label, unit, minimum relative change, minimum absolute change
    "activity_minutes": ("활동 시간", "분", 0.20, 10.0),
    "sleep_hours": ("수면 시간", "시간", 0.12, 0.5),
    "night_awakenings": ("야간 각성", "회", 0.30, 0.75),
    "meal_grams": ("식사량", "g", 0.15, 20.0),
    "evening_walk_minutes": ("저녁 산책", "분", 0.20, 7.0),
    "scratching_count": ("긁기", "회", 0.30, 1.5),
    "barking_count": ("짖음", "회", 0.30, 2.5),
}

ENVIRONMENT_METRICS = {
    "temperature_c": ("평균 기온", "°C"),
    "precipitation_mm": ("강수량", "mm"),
}
