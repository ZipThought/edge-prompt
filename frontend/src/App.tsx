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
import StudentDashboard from "./pages/student/studentDashboard";
import TeacherDashboard from "./pages/teacher/teacherDashboard";
import CreateClass from "./pages/teacher/createClass";
import ManageClass from "./pages/teacher/manageClass";
import ClassPage from "./pages/student/StudentClassPage";
import TeacherClassPage from "./pages/teacher/classPage";
import MaterialDetailPage from "./pages/teacher/materialDetailPage";
import ProjectDetailPage from "./pages/teacher/moduleView";
import StudentModulePage from "./pages/student/StudentModulePage";
import TeacherGradeClassPage from "./pages/teacher/classGradingPage";
import TeacherAssignStudentGradePage from "./pages/teacher/studentGradingPage";

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

            {/* Teacher dashboard */}
            <Route path="/dashboard/teacher" element={<TeacherDashboard />} />
            <Route path="/dashboard/teacher/create-class" element={<CreateClass />} />
            <Route path="/dashboard/teacher/class/:id" element={<TeacherClassPage />} />
            <Route path="/dashboard/teacher/manage-class/:classId" element={<ManageClass />} />
            <Route path="/material/:id" element={<MaterialDetailPage />} />
            <Route path="/dashboard/teacher/project/:id" element={<ProjectDetailPage />} />
            <Route path="/dashboard/teacher/grade/:classId" element={<TeacherGradeClassPage/>} />
            <Route path="/dashboard/teacher/grade/student/:studentId" element={<TeacherAssignStudentGradePage/>} />

            {/*student dashboard*/}
            <Route path="/dashboard/student" element={<StudentDashboard />} />
            <Route path="/dashboard/student/class/:classId" element={<ClassPage />} />
            <Route path="/dashboard/student/project/:projectId" element={<StudentModulePage />} />
            

            {/* Fallback route - redirect to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </ProjectProvider>
    </ErrorBoundary>
  );
};

export default App;