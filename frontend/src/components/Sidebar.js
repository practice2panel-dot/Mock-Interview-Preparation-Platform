import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  User, 
  Video, 
  BookOpen, 
  MessageCircle,
  Target,
  Home,
  Menu,
  X
} from 'lucide-react';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    // Set CSS variable for sidebar width
    document.documentElement.style.setProperty(
      '--sidebar-width',
      isOpen ? '260px' : '70px'
    );
  }, [isOpen]);

  const navItems = [
    { 
      path: '/', 
      label: 'Home', 
      icon: <Home size={20} /> 
    },
    { 
      path: '/profile', 
      label: 'Profile', 
      icon: <User size={20} /> 
    },
    { 
      path: '/mock-interview', 
      label: 'Mock Interview', 
      icon: <Video size={20} /> 
    },
    { 
      path: '/skill-prep', 
      label: 'Skill Prep', 
      icon: <BookOpen size={20} /> 
    },
    { 
      path: '/ai-assistant', 
      label: 'AI Assistant', 
      icon: <MessageCircle size={20} /> 
    }
  ];

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Target className="logo-icon" size={24} />
            <span className={`logo-text ${isOpen ? 'visible' : 'hidden'}`}>Practice2Panel</span>
          </div>
        </div>
        <nav className={`sidebar-nav ${!isOpen ? 'sidebar-nav-collapsed' : ''}`}>
          <button 
            className="sidebar-toggle sidebar-nav-item"
            onClick={toggleSidebar}
            aria-label="Toggle sidebar"
          >
            <span className="nav-icon">
              {isOpen ? <X size={20} /> : <Menu size={20} />}
            </span>
            {isOpen && <span className="nav-label">Menu</span>}
          </button>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                title={!isOpen ? item.label : ''}
              >
                <span className="nav-icon">{item.icon}</span>
                {isOpen && <span className="nav-label">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      </div>
      <div 
        className={`sidebar-overlay ${isOpen ? 'active' : ''}`} 
        onClick={toggleSidebar}
      ></div>
    </>
  );
};

export default Sidebar;

