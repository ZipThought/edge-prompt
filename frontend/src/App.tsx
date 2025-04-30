import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { ProjectProvider } from "./contexts/ProjectContext";
import { ErrorBoundary } from "./components/ErrorBoundary";

// Page imports
import HomePage from "./pages/homepage";
import SignUpPage from "./pages/signup";
import LoginPage from "./pages/signin";
import ProfilePage from "./pages/profile";
import Dashboard from "./pages/dashboard";
import StudentDashboard from "./pages/studentDashboard";
import TeacherDashboard from "./pages/teacher/teacherDashboard";
import CreateClass from "./pages/teacher/createClass";
import ManageClass from "./pages/teacher/manageClass";
import ClassPage from "./pages/StudentClassPage";
import TeacherClassPage from "./pages/teacher/classPage";

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ProjectProvider>
        <Router>
          <Routes>
            {/* Home page is the default route */}
            <Route path="/" element={<HomePage />} />

            {/* Authentication routes */}
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/profile" element={<ProfilePage />} />

            {/* Main dashboard */}
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/dashboard/student" element={<StudentDashboard />} />
            <Route path="/class/:classId" element={<ClassPage />} />

            {/* Teacher dashboard */}
            <Route path="/dashboard/teacher" element={<TeacherDashboard />} />
            <Route path="/dashboard/teacher/create-class" element={<CreateClass />} />
            <Route path="/dashboard/teacher/class/:id" element={<TeacherClassPage />} />
            <Route path="/dashboard/teacher/manage-class/:classId" element={<ManageClass />} />

            {/* Fallback route - redirect to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </ProjectProvider>
    </ErrorBoundary>
  );
};

export default App;