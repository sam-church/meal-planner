-- Check if the server is already running on port 5000
set serverRunning to false
try
    do shell script "lsof -ti :5000"
    set serverRunning to true
end try

if not serverRunning then
    tell application "Terminal"
        activate
        do script "cd ~/code/claude/meal-planner && source venv/bin/activate && python run.py"
    end tell
    -- Wait for server to be ready (up to 10 seconds)
    set attempts to 0
    repeat
        delay 1
        set attempts to attempts + 1
        try
            do shell script "curl -sf http://localhost:5000/api/weeks > /dev/null"
            exit repeat
        end try
        if attempts > 10 then exit repeat
    end repeat
end if

open location "http://localhost:5000"
