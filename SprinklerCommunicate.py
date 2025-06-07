# Imports
import psycopg2
import pandas as pd
from DataGathering import logSprinkler

# Parameters
spRate = 0 # Sprinkler Rate (ml/s)
desiredHyd = 0 # Desired Hydration (ml)
day = 3 # Sprinkler Frequency (days)
mqttRec = ""

# Postgres Information
db = "SprinklerWeatherData" # Name of Database
h = "localhost" # Host
u = "postgres" # User
p = "postgres" # Password
pt = 5432 # Port

# Connect to Postgres
conn = psycopg2.connect(database = db, user = u, host= h, password = p, port = pt)
cur = conn.cursor()

# Recording how long the sprinkler was on to the database (manual)
def recordMan():
    num = int(input("How long was the sprinkler on today? (to the nearest min):"))
    logSprinkler(num)

# Determines how long the sprinkler system should be on
def howLong(rate, desire):
    # SQL Command to gather predicted hydration for the next x days
    cur.execute("SELECT value AS precipitation FROM \"Daily\" "
                f"WHERE tag = 'precipitation_sum' AND time::date >= CURRENT_DATE AND time::date < CURRENT_DATE + INTERVAL '{day} days';")
    rows = cur.fetchall()
    conn.commit()
    pred = sum(row[0] for row in rows)

    amt = desire - pred # Sprinkler ammount of water = desired - predicted
    time = int(amt/rate)
    
    if (time <= 0): return 0
    else: return time

# Communicates with the sprinkler
def mqtt(spTime, rec):
    # TODO: Work with mqtt to send messages for the spinkler system to read
    print ("hello")

# Runs the whole process
def activate():
    time = howLong(spRate, desiredHyd)
    mqtt(time, mqttRec)
    logSprinkler(time)

# Close Connection
conn.close