graph LR
    %% 节点样式
    classDef normalModule fill:#bbf,stroke:#333,stroke-width:1px;
    classDef circularModule fill:#fbb,stroke:#f00,stroke-width:1px;
    classDef focusModule fill:#bfb,stroke:#0a0,stroke-width:2px;

    m1968["platform"]
    m1457["include"]
    m1968 -->|28文件| m1457
    m0730["firmware"]
    m0730 -->|2文件| m1457
    m3968["lib"]
    m3968 -->|428文件| m1457

    %% 应用节点样式
    class m1968 normalModule;
    class m1457 normalModule;
    class m0730 normalModule;
    class m1457 normalModule;
    class m3968 normalModule;
    class m1457 normalModule;
