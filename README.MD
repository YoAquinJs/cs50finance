# Stock Market Portfolio Simulator

This repository contains a Python Flask web application of a simulation of a stock market portfolio over time. Users can create an account, add stocks to their portfolio, and track the performance of their investments using real-time market data.

## Deployment

You can use [Finance]() app in here for testing it.

## Installation

Clone the repository:
```
git clone https://github.com/YoAquinJs/cs50finance.git finance
```
To run this application, you will need Python 3.x and Flask installed on your machine. Install [Flask](https://flask.palletsprojects.com/en/2.2.x/installation/). Then setup the flask project:
### Windows
```
cd finance
python3 -m venv venv
.venv/bin/activate
```
Then install the dependencies:
```
pip install cs50
pip install requests
pip install python-dotenv

```
Then run the app:
```
flask run
```
### Linux
Install the dependencies:
```
pip install flask
pip install cs50
pip install requests
pip install python-dotenv
```
Then run the app:
```
flask run
```

This will start the Flask development server, and the application will be accessible at `http://127.0.0.1:5000/` (may differ, check the terminal output).

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