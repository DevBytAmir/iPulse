*** Settings ***
Documentation     System-level acceptance tests for the HR measurement and
...               local HRV analysis flows, driven through MenuController
...               with hardware I/O stubbed (see AppLibrary.py).
Library           AppLibrary.py
Library           Collections
Test Setup        Start Application


*** Test Cases ***
Measure Heart Rate End To End
    [Documentation]    main_menu -> hr_instruction -> hr_measuring -> hr_stopped -> main_menu.
    State Should Be    main_menu

    # Menu cursor starts on item 0 (Measure HR); Select enters it directly.
    Press Select
    Tick
    State Should Be    hr_instruction

    Press Select
    Tick
    State Should Be    hr_measuring

    Simulate Ppg Seconds    5    70
    ${bpm}=    Current Bpm
    Should Be True    ${bpm} > 0    A 5 s / 70 BPM signal should have produced a live BPM reading

    Press Select
    Tick
    State Should Be    hr_stopped

    Press Select
    Tick
    State Should Be    main_menu

Run Local HRV Analysis Offline
    [Documentation]    main_menu -> hrv_instruction -> hrv_collecting -> hrv_results, fully offline.
    State Should Be    main_menu

    # Menu item 1 (HRV Analysis) is one Down press from the default cursor.
    Press Down
    Tick
    State Should Be    main_menu

    Press Select
    Tick
    State Should Be    hrv_instruction

    Press Select
    Tick
    State Should Be    hrv_collecting

    Run Hrv Collection    70
    State Should Be    hrv_results

    ${screen}=    Last Displayed Screen
    Should Be Equal    ${screen}    show_hrv_results

    Press Select
    Tick
    State Should Be    main_menu

HRV Analysis Completes When Network Is Unavailable
    [Documentation]    MenuController must reach hrv_results without blocking
    ...                or crashing when the network is offline.
    Press Down
    Tick
    Press Select
    Tick
    State Should Be    hrv_instruction

    Press Select
    Tick
    State Should Be    hrv_collecting

    Run Hrv Collection    70
    State Should Be    hrv_results

    ${calls}=    Network Calls
    List Should Contain Value    ${calls}    publish_hrv
    List Should Contain Value    ${calls}    db_add_record
