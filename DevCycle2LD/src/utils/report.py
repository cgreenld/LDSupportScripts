"""
Report Generator

Generates migration reports and summaries
"""

from datetime import datetime
from typing import Any, Dict, List


class ReportGenerator:
    """Generates migration reports and summaries."""
    
    def __init__(self):
        """Initialize report generator."""
        self.phases: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()
    
    def add_phase(self, phase_name: str, data: Dict[str, Any]):
        """Add a phase to the report."""
        self.phases.append({
            'name': phase_name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'data': data
        })
    
    def generate(self) -> Dict[str, Any]:
        """Generate the final report."""
        end_time = datetime.utcnow()
        duration_ms = int((end_time - self.start_time).total_seconds() * 1000)
        
        # Calculate summary statistics
        summary = self._calculate_summary()
        
        return {
            'migrationId': f"migration-{int(self.start_time.timestamp() * 1000)}",
            'startedAt': self.start_time.isoformat() + 'Z',
            'completedAt': end_time.isoformat() + 'Z',
            'durationMs': duration_ms,
            'durationFormatted': self._format_duration(duration_ms),
            'summary': summary,
            'phases': self.phases
        }
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics from all phases."""
        summary = {
            'environments': {'created': 0, 'skipped': 0, 'failed': 0},
            'features': {'extracted': 0, 'transformed': 0, 'created': 0, 'skipped': 0, 'failed': 0},
            'segments': {'extracted': 0, 'transformed': 0, 'created': 0, 'skipped': 0, 'failed': 0},
            'targeting': {'applied': 0, 'failed': 0},
            'success': True
        }
        
        for phase in self.phases:
            phase_name = phase['name']
            data = phase['data']
            
            if phase_name == 'extraction':
                summary['features']['extracted'] = data.get('features', 0)
                summary['segments']['extracted'] = data.get('audiences', 0)
            
            elif phase_name == 'transformation':
                summary['features']['transformed'] = data.get('flags', 0)
                summary['segments']['transformed'] = data.get('segments', 0)
            
            elif phase_name == 'loading':
                if 'environments' in data:
                    summary['environments']['created'] = len(data['environments'].get('created', []))
                    summary['environments']['skipped'] = len(data['environments'].get('skipped', []))
                    summary['environments']['failed'] = len(data['environments'].get('failed', []))
                
                if 'flags' in data:
                    summary['features']['created'] = len(data['flags'].get('created', []))
                    summary['features']['skipped'] = len(data['flags'].get('skipped', []))
                    summary['features']['failed'] = len(data['flags'].get('failed', []))
                
                if 'segments' in data:
                    summary['segments']['created'] = len(data['segments'].get('created', []))
                    summary['segments']['skipped'] = len(data['segments'].get('skipped', []))
                    summary['segments']['failed'] = len(data['segments'].get('failed', []))
                
                if 'targeting' in data:
                    summary['targeting']['applied'] = len(data['targeting'].get('applied', []))
                    summary['targeting']['failed'] = len(data['targeting'].get('failed', []))
        
        # Determine overall success
        summary['success'] = (
            summary['environments']['failed'] == 0 and
            summary['features']['failed'] == 0 and
            summary['segments']['failed'] == 0 and
            summary['targeting']['failed'] == 0
        )
        
        return summary
    
    def _format_duration(self, ms: int) -> str:
        """Format duration in human-readable format."""
        if ms < 1000:
            return f"{ms}ms"
        if ms < 60000:
            return f"{ms / 1000:.1f}s"
        
        minutes = ms // 60000
        seconds = round((ms % 60000) / 1000)
        return f"{minutes}m {seconds}s"

