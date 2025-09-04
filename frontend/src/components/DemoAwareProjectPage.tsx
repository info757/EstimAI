import React from 'react';
import { useParams } from 'react-router-dom';
import config from '../config';
import ProjectPage from '../pages/ProjectPage';
import DemoProjectPage from '../pages/DemoProjectPage';

export const DemoAwareProjectPage: React.FC = () => {
  const { pid } = useParams<{ pid: string }>();
  
  // Check if this is a demo project
  const isDemoProject = pid === config.demo.projectId;
  
  if (isDemoProject) {
    return <DemoProjectPage />;
  }
  
  return <ProjectPage />;
};

export default DemoAwareProjectPage;
