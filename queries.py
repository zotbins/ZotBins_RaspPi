'''
SQL Queries used for modifying data
'''

create_local_table = '''CREATE TABLE IF NOT EXISTS BINS ("TIMESTAMP" TEXT NOT NULL, "WEIGHT" REAL, "DISTANCE" REAL,"MESSAGES"  TEXT);'''

insert_data = "INSERT INTO BINS(TIMESTAMP,WEIGHT,DISTANCE,MESSAGES)\nVALUES('{}',{},{},'{}')"

select_data = "SELECT TIMESTAMP, WEIGHT, DISTANCE from BINS"

delete_data = "DELETE from BINS"