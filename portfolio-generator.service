[Unit]
Description=Portfolio Generator Service
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/script/directory
ExecStart=/usr/bin/python3 /path/to/script/directory/portfolio_generator.py
Restart=on-failure
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=portfolio-generator

[Install]
WantedBy=multi-user.target