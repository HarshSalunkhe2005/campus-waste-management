@echo off
echo Resetting the database.

cd C:\Users\Harsh\campus-waste

mysql -u root -p<db\campus_food_waste.sql

echo Database has been reset.

cd backend

start python app.py

timeout /t 10

start http://127.0.0.1:5000/

pause
