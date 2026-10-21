function conky_on_mouse(event)
    if event and event.type == "button_down" then
        if event.button == 1 or event.button == "1" or event.button == "left" then
            os.execute("konsole &")
        end
    end
end
