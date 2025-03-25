# Soccer Analyst Project

A real-time soccer analysis dashboard built with Python, Streamlit, and ChromaDB.

## Features

- League Overview with current standings and statistics
- Team Analysis with detailed comparisons
- Match Analysis with performance metrics
- Big Six Comparison
- Real-time data updates
- Data persistence using ChromaDB
- Comprehensive logging system

## Requirements

- Python 3.11+
- Streamlit
- ChromaDB
- Pandas
- Plotly
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd soccer_analyst_project
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with your API keys and configuration:
```
FOOTBALL_API_KEY=your_api_key_here
```

## Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

The application will be available at http://localhost:8501

## Project Structure

- `app.py`: Main Streamlit application
- `soccer_analyst.py`: Core analysis system
- `football_data_api.py`: API integration
- `vector_db.py`: ChromaDB integration
- `visualizer.py`: Data visualization
- `requirements.txt`: Project dependencies

## Logging

The application uses a comprehensive logging system that:
- Creates rotating log files in the `logs` directory
- Maintains log history with a maximum of 5 backup files
- Each log file has a maximum size of 5MB
- Logs both to file and console with different verbosity levels

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 