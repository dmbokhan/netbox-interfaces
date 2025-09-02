## Установка и настройка
1. Скачиваем проект
```
git clone <путь до репозитория>
```
2. Создаем venv 
```
cd netbox-interfaces
python -m venv venv
```
3. Переходим в venv
```
source venv/bin/activate
```
3. Устанавливаем зависимости
```
python -m pip install -r requirements.txt
```
4. Копируем примеры настроек и заполняем
```
cp settings_example.ini settings.ini
nano settings.ini
```

## Использование
1. Заполняем inventory.csv по примеру inventory_example.csv
2. Переходим в venv
```
source venv/bin/activate
```
3. Запускаем скрипт
```
python netbox-interfaces.py
```