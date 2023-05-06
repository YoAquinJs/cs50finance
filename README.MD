# Stock Market Portfolio Simulator

This repository contains a Python Flask web application of a simulation of a stock market portfolio over time. Users can create an account, add stocks to their portfolio, and track the performance of their investments using real-time market data.

## Deployment

You can use [Finance]() app in here for testing it.

## Requirements

You will need to install the next requirements for running the project on your own:

[Python3.x](https://www.python.org/downloads/)

[Flask](https://flask.palletsprojects.com/en/2.2.x/installation/)

[Sqlite](https://sqlite.org/index.html)

[Database Setup](./DATABASE.MD)

[Pip installs](./requirements.txt)
```
pip install -r requirements.txt
```

Then clone the repository:
```
git clone https://github.com/YoAquinJs/cs50finance.git finance
```

## Running 

To run this application setup virtual enviroment in the flask installation, then:
```
flask run
```

This will start a Flask development server, and the application will be accessible at `http://127.0.0.1:5000/`

## Features

- User account creation and authentication
- Portfolio management (add/remove stocks, view portfolio performance)
- Add mroe money(simulation) 
- Real-time market data from a third-party API
- Historical performance analysis

## Contributing

Contributions are welcome! You can submit bugs, feedback or pull requests. I will be gratefull to recive ideas for improving the project.

## License

This application is licensed under the [MIT License](https://opensource.org/licenses/MIT), see the license file.