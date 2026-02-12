import React from 'react';
import Editor from '@monaco-editor/react';

const SQLEditor = ({ value, onChange, dialect }) => {
    const handleEditorChange = (newValue) => {
        onChange(newValue || '');
    };

    const getLanguage = () => {
        switch (dialect) {
            case 'mysql':
                return 'mysql';
            case 'postgresql':
            case 'redshift':
                return 'pgsql';
            default:
                return 'sql';
        }
    };

    return (
        <div className="h-full w-full" data-testid="sql-editor">
            <Editor
                height="100%"
                defaultLanguage="sql"
                language={getLanguage()}
                value={value}
                onChange={handleEditorChange}
                theme="vs-dark"
                options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    fontFamily: "'JetBrains Mono', monospace",
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 2,
                    wordWrap: 'on',
                    padding: { top: 16, bottom: 16 },
                    renderLineHighlight: 'line',
                    cursorBlinking: 'smooth',
                    smoothScrolling: true,
                    contextmenu: true,
                    folding: true,
                    foldingStrategy: 'indentation',
                    showFoldingControls: 'mouseover',
                    bracketPairColorization: { enabled: true },
                    guides: {
                        indentation: true,
                        bracketPairs: true
                    },
                    suggest: {
                        showKeywords: true,
                        showSnippets: true
                    }
                }}
            />
        </div>
    );
};

export default SQLEditor;
