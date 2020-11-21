'''
SQL Queries used for modifying data
'''

create_local_table = '''CREATE TABLE IF NOT EXISTS BINS ("TIMESTAMP" TEXT NOT NULL, "WEIGHT" REAL, "DISTANCE" REAL,"MESSAGES"  TEXT);'''

create_local_error_table = '''CREATE TABLE IF NOT EXISTS ERROR ("TIMESTAMP" TEXT NOT NULL, "WEIGHT_SENSOR_ID"  TEXT, "FAILURE"  TEXT);'''

insert_data = "INSERT INTO BINS(TIMESTAMP,WEIGHT,DISTANCE,MESSAGES)\nVALUES('{}',{},{},'{}')"

insert_error_data = "INSERT INTO ERROR (TIMESTAMP,WEIGHT_SENSOR_ID,FAILURE)\nVALUES('{}', '{}','{}')"

select_data = "SELECT TIMESTAMP, WEIGHT, DISTANCE from BINS"

select_error_data = "SELECT TIMESTAMP, WEIGHT_SENSOR_ID, FAILURE from ERROR"

delete_data = "DELETE from BINS"

delete_error_data = "DELETE from ERROR"