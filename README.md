# DSA Ambulance Routing System

A comprehensive ambulance routing system that uses graph algorithms and real-time traffic data to optimize emergency medical response times. The system features a FastAPI backend with Dijkstra's algorithm for shortest path calculation and a Next.js frontend with interactive mapping.
<br>
<p align="center">
  <img width="851" height="356" alt="image" src="https://github.com/user-attachments/assets/533f7d0f-c9d8-4d81-9829-86f591aa2995" />
  <br>
   <br>
  <img width="843" height="539" alt="image" src="https://github.com/user-attachments/assets/3a22a628-15ba-475b-9d33-cb83e9646ec2" />
  <br /> <br>
  <img width="803" height="501" alt="image" src="https://github.com/user-attachments/assets/fa829660-b6c0-410a-960b-59b5c680db9b" />
</p>



## Features

- **Real-time Ambulance Assignment**: Automatically assigns the nearest available ambulance to emergency requests
- **Dynamic Traffic Management**: Adjusts route calculations based on current traffic conditions
- **Interactive Map Visualization**: Live tracking of ambulance movements and routes using Leaflet
- **Hospital Selection**: Automatically selects the nearest hospital based on traffic and distance
- **WebSocket Communication**: Real-time updates for ambulance status and ETA calculations
- **Debug Visualization**: Step-by-step visualization of Dijkstra's algorithm for educational purposes

## Architecture

### Backend (FastAPI)
- **Database**: MySQL with SQLAlchemy ORM
- **Routing Engine**: Custom implementation of Dijkstra's algorithm
- **Real-time Updates**: WebSocket support for live tracking
- **Traffic Management**: Dynamic weight adjustment based on traffic updates

### Frontend (Next.js)
- **UI Framework**: React with TypeScript
- **Styling**: Tailwind CSS with shadcn/ui components
- **Mapping**: Leaflet.js for interactive maps
- **State Management**: React hooks and context

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- MySQL Server
- Git

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd "DSA-Ambulance Routing"
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration

1. **Install MySQL Server** and ensure it's running
2. **Create Database**:
   ```sql
   CREATE DATABASE ambulance_routing;
   ```
3. **Update Database Connection** in `backend/app/db/database.py`:
   ```python
   SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://username:password@localhost/ambulance_routing"
   ```

4. **Create Tables**:
   ```bash
   python -m app.create_tables
   ```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

## Running the Application

### 1. Start the Backend Server
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`

### 2. Start the Frontend Development Server
```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Database Schema

The system uses the following main entities:

- **Cities**: Geographic areas containing nodes and edges
- **Nodes**: Locations (intersections, hospitals, ambulance stations)
- **Edges**: Roads connecting nodes with weights (travel time)
- **Ambulances**: Emergency vehicles with status and location
- **Emergency Requests**: Patient calls requiring ambulance dispatch
- **Assignments**: Links between ambulances and emergency requests
- **Traffic Updates**: Real-time traffic data affecting edge weights
- **Roadblocks**: Temporary road closures

## API Endpoints

### Routing
- `POST /route/requests/auto` - Create emergency request with auto hospital selection
- `GET /route/cities/{city_id}/hospitals` - List hospitals in a city
- `GET /route/requests/{request_id}/debug/dijkstra` - Debug Dijkstra visualization

### Traffic Management
- `POST /traffic/update` - Update traffic conditions
- `GET /traffic/current` - Get current traffic status

### Ambulance Management
- `GET /ambulance/` - List all ambulances
- `POST /ambulance/` - Add new ambulance
- `PUT /ambulance/{id}/status` - Update ambulance status

### WebSocket
- `WS /ws/ambulance/{request_id}` - Real-time updates for ambulance tracking

## Core Algorithms

### Dijkstra's Algorithm Implementation
The system uses a custom implementation of Dijkstra's algorithm to find the shortest path between nodes, considering:
- Base travel time (edge weights)
- Dynamic traffic adjustments
- Road closures and obstacles

### Ambulance Assignment Logic
1. **Request Processing**: Receives emergency request with location
2. **Hospital Selection**: Finds nearest hospital using modified Dijkstra
3. **Ambulance Selection**: Identifies nearest available ambulance
4. **Route Calculation**: Computes optimal route considering traffic
5. **Assignment Creation**: Links ambulance to request with ETA

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📁 Project Structure

```
DSA-Ambulance Routing/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── routing/          # Routing algorithms
│   │   │   └── graph/            # Graph management
│   │   ├── db/
│   │   │   ├── models.py         # Database models
│   │   │   └── database.py       # Database connection
│   │   ├── routers/              # API endpoints
│   │   └── main.py               # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── app/                      # Next.js app directory
│   ├── components/               # React components
│   ├── lib/                     # Utility functions
│   └── package.json
└── README.md
```

## Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```env
DATABASE_URL=mysql+mysqlconnector://username:password@localhost/ambulance_routing
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]
```

## Deployment

### Backend (Production)
```bash
# Using Gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend (Production)
```bash
cd frontend
npm run build
npm start
```

